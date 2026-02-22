#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Tile Generator API

Provides endpoints for generating .mbtiles files from GeoJSON sources
using tippecanoe. Supports two output modes:
  - "download": keep file locally, serve via download endpoint
  - "minio": upload to managed object store (MinIO)

Routes:
    GET  /tile-generator/sources              - List available GeoJSON sources
    POST /tile-generator/generate             - Start tile generation job
    GET  /tile-generator/status/{job_id}      - Check job status
    GET  /tile-generator/download/{job_id}    - Download completed .mbtiles file
"""

from objectTreeDecorators import treeObject, treeObjectInit
import falcon
import json
import os
import subprocess
import tempfile
import threading
import time
import uuid


class TileGeneratorAPI(treeObject):
    """API for generating .mbtiles from GeoJSON sources using tippecanoe."""

    @treeObjectInit
    def __init__(self, polServer, manager=None):
        self.polServer = polServer
        self.apiName = '/tile-generator'
        # Track generation jobs
        self._jobs = {}
        # Cache of locally-downloaded .mbtiles files: { "tileset_name": "/tmp/path.mbtiles" }
        self._mbtiles_cache = {}
        # Lock to prevent concurrent downloads of the same file
        import threading
        self._download_locks = {}
        self._download_locks_lock = threading.Lock()
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName + '/sources', self, suffix='sources')
            polServer.falconServer.add_route(self.apiName + '/generate', self, suffix='generate')
            polServer.falconServer.add_route(self.apiName + '/status/{job_id}', self, suffix='status')
            polServer.falconServer.add_route(self.apiName + '/download/{job_id}', self, suffix='download')
            polServer.falconServer.add_route(self.apiName + '/mbtiles', self, suffix='mbtiles')
            polServer.falconServer.add_route('/tiles/{tileset}/{z}/{x}/{y}', self, suffix='tile')

    def on_get_sources(self, request, response):
        """List all available GeoJSON sources for tile generation.

        Sources include:
        1. Classes with GeoJsonDefinition configs
        2. Classes with geoJson format endpoint enabled
        3. External API endpoints that return GeoJSON
        """
        try:
            sources = []

            # 1. Classes with GeoJsonDefinition configs
            if 'GeoJsonDefinition' in self.manager.objectTables:
                for defId, defInstance in self.manager.objectTables['GeoJsonDefinition'].items():
                    sourceClass = getattr(defInstance, 'source_class', '')
                    defName = getattr(defInstance, 'name', '')
                    # Count instances of the source class
                    instanceCount = 0
                    if sourceClass in self.manager.objectTables:
                        instanceCount = len(self.manager.objectTables[sourceClass])

                    sources.append({
                        "type": "class",
                        "className": sourceClass,
                        "geoJsonConfigId": defId,
                        "geoJsonConfigName": defName,
                        "instanceCount": instanceCount,
                        "hasGeoJsonEndpoint": self._classHasGeoJsonEndpoint(sourceClass)
                    })

            # 2. APIEndpoints that might serve GeoJSON
            if 'APIEndpoint' in self.manager.objectTables:
                for epId, epInstance in self.manager.objectTables['APIEndpoint'].items():
                    epName = getattr(epInstance, 'name', '')
                    epUrl = getattr(epInstance, 'url', '')
                    sources.append({
                        "type": "endpoint",
                        "endpointName": epName,
                        "endpointId": epId,
                        "url": epUrl
                    })

            response.media = {"success": True, "sources": sources}
            response.status = falcon.HTTP_200

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[TileGeneratorAPI] Error listing sources: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_post_generate(self, request, response):
        """Generate .mbtiles from selected sources.

        Request body:
        {
            "name": "my-tileset",
            "sources": [
                {"type": "class", "className": "City", "geoJsonConfigId": "abc"},
                {"type": "url", "url": "https://example.com/data.geojson"}
            ],
            "options": {
                "minZoom": 0,
                "maxZoom": 14,
                "layerName": "default"
            },
            "outputMode": "download" | "minio",
            "minioBucket": "polari-tiles"
        }
        """
        try:
            body = request.media
            if body is None:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "Request body is required"}
                return

            name = body.get('name', f'tileset-{int(time.time())}')
            sources = body.get('sources', [])
            options = body.get('options', {})
            output_mode = body.get('outputMode', 'download')
            minio_bucket = body.get('minioBucket', 'polari-tiles')

            if not sources:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "At least one source is required"}
                return

            # Validate minio mode has object store connected
            if output_mode == 'minio':
                store = getattr(self.manager, 'objectStore', None)
                if store is None or not store.connected:
                    response.status = falcon.HTTP_400
                    response.media = {"success": False, "error": "Object storage not connected. Use 'download' mode or connect MinIO first."}
                    return

            # Create a job ID
            job_id = str(uuid.uuid4())[:8]
            self._jobs[job_id] = {
                "id": job_id,
                "name": name,
                "status": "pending",
                "progress": "Queued for processing",
                "startedAt": time.time(),
                "completedAt": None,
                "outputPath": None,
                "downloadUrl": None,
                "error": None
            }

            # Run tile generation in a background thread
            thread = threading.Thread(
                target=self._run_generation_job,
                args=(job_id, name, sources, options, output_mode, minio_bucket),
                daemon=True
            )
            thread.start()

            response.status = falcon.HTTP_202
            response.media = {
                "success": True,
                "jobId": job_id,
                "message": f"Tile generation job '{name}' started",
                "statusUrl": f"/tile-generator/status/{job_id}"
            }

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[TileGeneratorAPI] Error starting generation: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_get_status(self, request, response, job_id):
        """Check the status of a tile generation job."""
        job = self._jobs.get(job_id)
        if job is None:
            response.status = falcon.HTTP_404
            response.media = {"success": False, "error": f"Job '{job_id}' not found"}
            return

        response.status = falcon.HTTP_200
        response.media = {"success": True, "job": job}
        response.set_header('Powered-By', 'Polari')

    def on_get_download(self, request, response, job_id):
        """Download the generated .mbtiles file for a completed job."""
        job = self._jobs.get(job_id)
        if job is None:
            response.status = falcon.HTTP_404
            response.media = {"success": False, "error": f"Job '{job_id}' not found"}
            return

        if job['status'] != 'completed':
            response.status = falcon.HTTP_400
            response.media = {"success": False, "error": f"Job is not completed (status: {job['status']})"}
            return

        output_path = job.get('outputPath', '')
        if not output_path or not os.path.exists(output_path):
            response.status = falcon.HTTP_404
            response.media = {"success": False, "error": "Output file not found on disk"}
            return

        file_name = os.path.basename(output_path)
        response.content_type = 'application/octet-stream'
        response.set_header('Content-Disposition', f'attachment; filename="{file_name}"')

        with open(output_path, 'rb') as f:
            response.data = f.read()

        response.status = falcon.HTTP_200

    def _classHasGeoJsonEndpoint(self, className):
        """Check if a class has the GeoJSON format endpoint enabled."""
        if className in self.manager.objectTypingDict:
            typingObj = self.manager.objectTypingDict[className]
            formatConfig = getattr(typingObj, 'apiFormatConfig', None)
            if formatConfig is not None:
                return formatConfig.geoJsonEnabled
        return False

    def _run_generation_job(self, job_id, name, sources, options, output_mode, minio_bucket):
        """Background thread for tile generation."""
        job = self._jobs[job_id]
        job['status'] = 'running'
        tmpdir = None

        try:
            tmpdir = tempfile.mkdtemp(prefix='polari-tiles-')
            input_files = []

            # Step 1: Generate/fetch GeoJSON for each source
            for i, source in enumerate(sources):
                job['progress'] = f"Processing source {i+1}/{len(sources)}"
                source_type = source.get('type', '')

                if source_type == 'class':
                    geojson = self._generate_geojson_for_class(
                        source.get('className', ''),
                        source.get('geoJsonConfigId', '')
                    )
                elif source_type == 'url':
                    geojson = self._fetch_geojson_from_url(source.get('url', ''))
                elif source_type == 'endpoint':
                    geojson = self._fetch_geojson_from_endpoint(source.get('endpointName', ''))
                else:
                    print(f"[TileGeneratorAPI] Unknown source type: {source_type}")
                    continue

                feature_count = len(geojson.get('features', [])) if geojson else 0
                print(f"[TileGeneratorAPI] Source {i+1} result: geojson={'present' if geojson else 'None'}, features={feature_count}")
                if geojson and geojson.get('features'):
                    filepath = os.path.join(tmpdir, f'source_{i}.geojson')
                    with open(filepath, 'w') as f:
                        json.dump(geojson, f)
                    input_files.append(filepath)
                    print(f"[TileGeneratorAPI] Wrote {feature_count} features to {filepath}")

            if not input_files:
                job['status'] = 'failed'
                job['error'] = 'No valid GeoJSON data found from any source'
                job['completedAt'] = time.time()
                return

            # Step 2: Run tippecanoe
            job['progress'] = 'Running tippecanoe...'
            output_path = os.path.join(tmpdir, f'{name}.mbtiles')
            self._run_tippecanoe(input_files, output_path, options)

            if not os.path.exists(output_path):
                job['status'] = 'failed'
                job['error'] = 'tippecanoe did not produce output file'
                job['completedAt'] = time.time()
                return

            # Step 3: Handle output based on mode
            if output_mode == 'minio':
                job['progress'] = 'Uploading to MinIO...'
                store = getattr(self.manager, 'objectStore', None)
                if store is None or not store.connected:
                    job['status'] = 'failed'
                    job['error'] = 'Object storage disconnected during generation'
                    job['completedAt'] = time.time()
                    return
                object_name = f'{name}.mbtiles'
                minio_path = store.upload_file(minio_bucket, object_name, output_path)
                job['outputPath'] = minio_path
                print(f"[TileGeneratorAPI] Uploaded to MinIO: {minio_path}")
                # Auto-register a TileSourceDefinition for the uploaded tileset
                self._register_tile_source(name, minio_bucket, object_name)
            else:
                # download mode — keep file in temp dir for download endpoint
                job['outputPath'] = output_path
                job['downloadUrl'] = f'/tile-generator/download/{job_id}'

            job['status'] = 'completed'
            job['progress'] = 'Done'
            job['completedAt'] = time.time()
            print(f"[TileGeneratorAPI] Job {job_id} completed: {job['outputPath']}")

        except Exception as e:
            job['status'] = 'failed'
            job['error'] = str(e)
            job['completedAt'] = time.time()
            print(f"[TileGeneratorAPI] Job {job_id} failed: {e}")
            import traceback
            traceback.print_exc()

    def _generate_geojson_for_class(self, className, geoJsonConfigId):
        """Build a GeoJSON FeatureCollection from class instances using GeoJsonDefinition."""
        if not className:
            print(f"[TileGeneratorAPI] _generate_geojson_for_class: className is empty")
            return None

        print(f"[TileGeneratorAPI] Generating GeoJSON for class='{className}', configId='{geoJsonConfigId}'")

        # Find the GeoJsonDefinition
        geoDef = None
        if 'GeoJsonDefinition' in self.manager.objectTables:
            geoDefTable = self.manager.objectTables['GeoJsonDefinition']
            print(f"[TileGeneratorAPI] GeoJsonDefinition table has {len(geoDefTable)} entries: {list(geoDefTable.keys())}")
            if geoJsonConfigId:
                geoDef = geoDefTable.get(geoJsonConfigId)
                if geoDef is None:
                    print(f"[TileGeneratorAPI] Config ID '{geoJsonConfigId}' not found in GeoJsonDefinition table")
            else:
                # Find first matching definition for this class
                for defId, defInstance in geoDefTable.items():
                    srcClass = getattr(defInstance, 'source_class', '')
                    print(f"[TileGeneratorAPI]   Checking defId={defId}, source_class='{srcClass}'")
                    if srcClass == className:
                        geoDef = defInstance
                        break
        else:
            print(f"[TileGeneratorAPI] 'GeoJsonDefinition' not in manager.objectTables")

        if geoDef is None:
            print(f"[TileGeneratorAPI] No GeoJsonDefinition found for {className}")
            return None

        # Parse definition
        definitionStr = getattr(geoDef, 'definition', '{}')
        print(f"[TileGeneratorAPI] GeoJsonDefinition.definition = {definitionStr}")
        try:
            definitionData = json.loads(definitionStr) if isinstance(definitionStr, str) else definitionStr
        except (json.JSONDecodeError, ValueError):
            print(f"[TileGeneratorAPI] Failed to parse definition JSON")
            definitionData = {}

        coordConfig = definitionData.get('geoJsonConfig', definitionData)
        print(f"[TileGeneratorAPI] coordConfig = {coordConfig}")

        # Get instances from DB
        db = getattr(self.manager, 'db', None)
        if db is None:
            print(f"[TileGeneratorAPI] manager.db is None")
            return None
        if className not in db.tables:
            print(f"[TileGeneratorAPI] '{className}' not in db.tables. Available tables: {db.tables}")
            return None

        try:
            columnNames, dataTuples = db.getAllInTable(className)
        except Exception as e:
            print(f"[TileGeneratorAPI] Error reading {className}: {e}")
            import traceback
            traceback.print_exc()
            return None

        print(f"[TileGeneratorAPI] DB returned {len(dataTuples)} rows, columns: {columnNames}")
        if dataTuples:
            print(f"[TileGeneratorAPI] First row sample: {dataTuples[0]}")

        # Build features
        features = []
        for row in dataTuples:
            instance = {}
            for i, colName in enumerate(columnNames):
                instance[colName] = row[i]

            lng, lat = self._parse_coordinates(instance, coordConfig)
            if lng is None or lat is None:
                if not features:  # Only log first failure to avoid spam
                    print(f"[TileGeneratorAPI] Coordinate extraction failed for first row. instance keys={list(instance.keys())}")
            else:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lng, lat]},
                    "properties": instance
                })

        print(f"[TileGeneratorAPI] Built {len(features)} features from {len(dataTuples)} rows")
        return {"type": "FeatureCollection", "features": features}

    def _parse_coordinates(self, instance, coordConfig):
        """Extract coordinates from instance using coordinate config."""
        coordinateMode = coordConfig.get('coordinateMode', 'separate')
        lng = None
        lat = None

        if coordinateMode == 'tuple':
            tupleVar = coordConfig.get('tupleVariable', '')
            tupleOrder = coordConfig.get('tupleOrder', 'lat-lng')
            if tupleVar and tupleVar in instance:
                val = instance[tupleVar]
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except (json.JSONDecodeError, ValueError):
                        return None, None
                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    try:
                        if tupleOrder == 'lat-lng':
                            lat, lng = float(val[0]), float(val[1])
                        else:
                            lng, lat = float(val[0]), float(val[1])
                    except (ValueError, TypeError):
                        return None, None

        elif coordinateMode == 'separate':
            latVar = coordConfig.get('latitudeVariable', '')
            lngVar = coordConfig.get('longitudeVariable', '')
            try:
                if latVar and latVar in instance:
                    lat = float(instance[latVar])
                if lngVar and lngVar in instance:
                    lng = float(instance[lngVar])
            except (ValueError, TypeError):
                pass

        return lng, lat

    def _fetch_geojson_from_url(self, url):
        """Fetch GeoJSON from an external URL."""
        if not url:
            return None
        try:
            import requests
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[TileGeneratorAPI] Error fetching URL {url}: {e}")
            return None

    def _fetch_geojson_from_endpoint(self, endpointName):
        """Fetch GeoJSON from a configured APIEndpoint."""
        if not endpointName or 'APIEndpoint' not in self.manager.objectTables:
            return None

        endpoint = None
        for epId, epInstance in self.manager.objectTables['APIEndpoint'].items():
            if getattr(epInstance, 'name', '') == endpointName:
                endpoint = epInstance
                break

        if endpoint is None:
            return None

        url = getattr(endpoint, 'url', '')
        return self._fetch_geojson_from_url(url)

    def _run_tippecanoe(self, input_files, output_path, options):
        """Run tippecanoe subprocess to generate .mbtiles."""
        cmd = ['tippecanoe', '-o', output_path, '--force']

        min_zoom = options.get('minZoom', 0)
        max_zoom = options.get('maxZoom', 14)
        layer_name = options.get('layerName', 'default')

        cmd.extend(['-z', str(max_zoom)])
        cmd.extend(['-Z', str(min_zoom)])
        cmd.extend(['-l', layer_name])

        # Add input files
        cmd.extend(input_files)

        print(f"[TileGeneratorAPI] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or 'Unknown error'
            raise RuntimeError(f"tippecanoe failed (exit {result.returncode}): {error_msg}")

        print(f"[TileGeneratorAPI] tippecanoe completed successfully: {output_path}")

    def _register_tile_source(self, name, bucket, object_name):
        """Auto-create a TileSourceDefinition for an uploaded .mbtiles file."""
        try:
            if 'TileSourceDefinition' not in self.manager.objectTables:
                print("[TileGeneratorAPI] TileSourceDefinition not in objectTables, skipping auto-register")
                return

            # Check if a definition with this name already exists
            for defId, defInstance in self.manager.objectTables['TileSourceDefinition'].items():
                if getattr(defInstance, 'name', '') == name:
                    print(f"[TileGeneratorAPI] TileSourceDefinition '{name}' already exists, skipping")
                    return

            from polariApiServer.tileSourceDefinition import TileSourceDefinition
            definition = json.dumps({
                'type': 'vector',
                'url': f'/tiles/{name}/{{z}}/{{x}}/{{y}}.pbf',
                'bucket': bucket,
                'objectName': object_name,
                'attribution': 'Generated by Polari Tile Generator',
                'tileFormat': 'vector',
                'sourceLayer': 'default'
            })
            tileSrc = TileSourceDefinition(
                name=name, type='tileserver', definition=definition,
                manager=self.manager
            )
            # Persist to DB
            db = getattr(self.manager, 'db', None)
            if db is not None:
                polariId = getattr(tileSrc, 'polariId', None)
                if polariId:
                    self.manager.objectTables['TileSourceDefinition'][polariId] = tileSrc
                    db.saveInstanceInDB(tileSrc)
                    print(f"[TileGeneratorAPI] Auto-registered TileSourceDefinition '{name}' (id={polariId})")
        except Exception as e:
            print(f"[TileGeneratorAPI] Failed to auto-register tile source: {e}")
            import traceback
            traceback.print_exc()

    def on_get_mbtiles(self, request, response):
        """GET /tile-generator/mbtiles - List .mbtiles files in object storage."""
        try:
            store = getattr(self.manager, 'objectStore', None)
            if store is None or not store.connected:
                response.media = {"success": True, "files": [], "connected": False}
                response.status = falcon.HTTP_200
                response.set_header('Powered-By', 'Polari')
                return

            # Collect .mbtiles files across all buckets
            files = []
            for bucket_name in store.buckets:
                try:
                    objects = store.list_objects(bucket_name)
                    for obj in objects:
                        obj_name = obj.get('name', '')
                        if obj_name.endswith('.mbtiles'):
                            files.append({
                                'bucket': bucket_name,
                                'name': obj_name,
                                'size': obj.get('size', 0),
                                'lastModified': obj.get('lastModified'),
                                'path': f'{bucket_name}/{obj_name}'
                            })
                except Exception as e:
                    print(f"[TileGeneratorAPI] Error listing bucket {bucket_name}: {e}")

            response.media = {"success": True, "files": files, "connected": True}
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[TileGeneratorAPI] Error listing mbtiles: {err}")
        response.set_header('Powered-By', 'Polari')

    # ===================== Tile Serving =====================

    def on_get_tile(self, request, response, tileset, z, x, y):
        """GET /tiles/{tileset}/{z}/{x}/{y} - Serve an individual tile from an .mbtiles file.

        Looks up the tileset name in TileSourceDefinition instances to find the
        bucket/object, downloads the .mbtiles from MinIO if not cached, and
        reads the tile from the SQLite database.
        """
        import sqlite3
        import traceback as tb

        # Always set CORS headers (even on errors)
        response.set_header('Access-Control-Allow-Origin', '*')
        response.set_header('Access-Control-Allow-Headers', '*')

        try:
            print(f"[TileServe] Request: /tiles/{tileset}/{z}/{x}/{y}", flush=True)

            # Strip file extension from y (e.g. "5.pbf" -> "5", "5.png" -> "5")
            if isinstance(y, str) and '.' in y:
                y = y.rsplit('.', 1)[0]

            try:
                z, x, y = int(z), int(x), int(y)
            except (ValueError, TypeError):
                print(f"[TileServe] ERROR: z/x/y not integers: z={z} x={x} y={y}", flush=True)
                response.status = falcon.HTTP_400
                response.media = {"error": "z, x, y must be integers"}
                return

            local_path = self._resolve_mbtiles_path(tileset)
            if local_path is None:
                print(f"[TileServe] ERROR: Tileset '{tileset}' not found (no mbtiles resolved)", flush=True)
                response.status = falcon.HTTP_404
                response.media = {"error": f"Tileset '{tileset}' not found"}
                return

            # Log file info
            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else -1
            print(f"[TileServe] Resolved mbtiles path: {local_path} (size={file_size} bytes)", flush=True)

            # mbtiles uses TMS y-coordinate (flipped)
            tms_y = (1 << z) - 1 - y

            conn = sqlite3.connect(local_path)
            try:
                # Determine schema: flat (tiles table/view) vs normalized (map+images)
                schema_cursor = conn.execute(
                    "SELECT name, type FROM sqlite_master WHERE type IN ('table','view')"
                )
                schema = {row[0]: row[1] for row in schema_cursor.fetchall()}

                if 'tiles' in schema:
                    # Flat schema or tiles view — query directly
                    cursor = conn.execute(
                        'SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?',
                        (z, x, tms_y)
                    )
                elif 'map' in schema and 'images' in schema:
                    # Normalized schema (tippecanoe default): map + images tables
                    cursor = conn.execute(
                        'SELECT images.tile_data FROM map '
                        'JOIN images ON map.tile_id = images.tile_id '
                        'WHERE map.zoom_level = ? AND map.tile_column = ? AND map.tile_row = ?',
                        (z, x, tms_y)
                    )
                else:
                    print(f"[TileServe] ERROR: Unrecognized mbtiles schema: {list(schema.keys())}", flush=True)
                    response.status = falcon.HTTP_500
                    response.media = {"error": f"Unrecognized mbtiles schema. Found: {list(schema.keys())}"}
                    return

                row = cursor.fetchone()
            finally:
                conn.close()

            if row is None:
                response.status = falcon.HTTP_204
                return

            tile_data = row[0]
            print(f"[TileServe] Tile z={z} x={x} y={y} (tms_y={tms_y}): {len(tile_data)} bytes, first2=0x{tile_data[:2].hex()}", flush=True)

            # Detect tile format: PBF vector tiles start with gzip magic bytes
            # or are raw protobuf. PNG starts with \x89PNG, JPEG with \xff\xd8.
            if tile_data[:2] == b'\x1f\x8b':
                # gzip-compressed PBF (vector tile)
                response.content_type = 'application/x-protobuf'
                response.set_header('Content-Encoding', 'gzip')
            elif tile_data[:4] == b'\x89PNG':
                response.content_type = 'image/png'
            elif tile_data[:2] == b'\xff\xd8':
                response.content_type = 'image/jpeg'
            else:
                # Assume PBF
                response.content_type = 'application/x-protobuf'

            response.set_header('Cache-Control', 'public, max-age=86400')
            response.data = tile_data
            response.status = falcon.HTTP_200

        except Exception as e:
            error_trace = tb.format_exc()
            print(f"[TileServe] UNHANDLED ERROR: {e}\n{error_trace}", flush=True)
            response.status = falcon.HTTP_500
            response.media = {"error": str(e), "traceback": error_trace}

    def _get_download_lock(self, tileset_name):
        """Get or create a per-tileset lock to prevent concurrent downloads."""
        with self._download_locks_lock:
            if tileset_name not in self._download_locks:
                import threading
                self._download_locks[tileset_name] = threading.Lock()
            return self._download_locks[tileset_name]

    def _resolve_mbtiles_path(self, tileset_name):
        """Resolve a tileset name to a local .mbtiles file path.

        Checks the mbtiles cache first, then looks up TileSourceDefinition
        to find the bucket/object and downloads from MinIO.
        Uses per-tileset locking to prevent concurrent downloads that
        corrupt the file.
        """
        print(f"[TileResolve] Resolving tileset: '{tileset_name}'", flush=True)

        # Check cache (fast path — no lock needed)
        if tileset_name in self._mbtiles_cache:
            cached = self._mbtiles_cache[tileset_name]
            if os.path.exists(cached):
                print(f"[TileResolve] Cache hit: {cached}", flush=True)
                return cached

        # Acquire per-tileset lock so only one thread downloads at a time
        lock = self._get_download_lock(tileset_name)
        with lock:
            # Double-check cache after acquiring lock (another thread may have downloaded)
            if tileset_name in self._mbtiles_cache:
                cached = self._mbtiles_cache[tileset_name]
                if os.path.exists(cached):
                    print(f"[TileResolve] Cache hit (after lock): {cached}", flush=True)
                    return cached

            # Look up the TileSourceDefinition to find bucket/object
            bucket = None
            object_name = None
            if 'TileSourceDefinition' in self.manager.objectTables:
                defs_count = len(self.manager.objectTables['TileSourceDefinition'])
                print(f"[TileResolve] Searching {defs_count} TileSourceDefinition(s)", flush=True)
                for defId, defInstance in self.manager.objectTables['TileSourceDefinition'].items():
                    inst_name = getattr(defInstance, 'name', '')
                    if inst_name == tileset_name:
                        defStr = getattr(defInstance, 'definition', '{}')
                        print(f"[TileResolve]   MATCH id={defId}, definition={defStr}", flush=True)
                        try:
                            defData = json.loads(defStr) if isinstance(defStr, str) else defStr
                        except (json.JSONDecodeError, ValueError):
                            defData = {}
                        stored_bucket = defData.get('bucket', '')
                        stored_obj = defData.get('objectName', '')
                        url = defData.get('url', '')
                        if stored_bucket and stored_obj:
                            bucket = stored_bucket
                            object_name = stored_obj
                        elif '/' in url:
                            clean = url.replace('s3://', '')
                            parts = clean.split('/', 1)
                            if len(parts) == 2:
                                bucket = parts[0]
                                object_name = parts[1]
                        break
            else:
                print(f"[TileResolve] TileSourceDefinition NOT in objectTables", flush=True)

            if not bucket or not object_name:
                # Fallback: scan all buckets for {tileset_name}.mbtiles
                print(f"[TileResolve] Fallback: scanning MinIO buckets", flush=True)
                store = getattr(self.manager, 'objectStore', None)
                if store and store.connected:
                    for b in store.buckets:
                        objects = store.list_objects(b)
                        for obj in objects:
                            oname = obj.get('name', '')
                            if oname == f'{tileset_name}.mbtiles':
                                bucket = b
                                object_name = oname
                                break
                        if bucket:
                            break

            if not bucket or not object_name:
                print(f"[TileResolve] FAILED to resolve tileset '{tileset_name}'", flush=True)
                return None

            # Download from MinIO to a temp file, then atomic rename
            store = getattr(self.manager, 'objectStore', None)
            if store is None or not store.connected:
                print(f"[TileResolve] objectStore not available for download", flush=True)
                return None

            cache_dir = os.path.join(tempfile.gettempdir(), 'polari-tile-cache')
            os.makedirs(cache_dir, exist_ok=True)
            local_path = os.path.join(cache_dir, f'{tileset_name}.mbtiles')
            tmp_path = local_path + '.downloading'

            try:
                store.download_file(bucket, object_name, tmp_path)
                # Atomic rename so readers never see a partial file
                os.replace(tmp_path, local_path)
                self._mbtiles_cache[tileset_name] = local_path
                print(f"[TileResolve] Downloaded and cached: {bucket}/{object_name} -> {local_path}", flush=True)
                return local_path
            except Exception as e:
                # Clean up partial download
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                print(f"[TileResolve] Failed to download {bucket}/{object_name}: {e}", flush=True)
                return None
