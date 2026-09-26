"""
@module tensormath.objects.tensormath.FEMFieldState

Row class FEMFieldState of the tensormath module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FEMFieldState(treeObject):
    """AN FEM ELEMENT FIELD AS A ROW — the materialisation that lets a sim-space binding SEE it (tt-6).

    The engine's tensorField (u per node, ε/σ per element) is a computed array, not a row, so until tt-6 no
    binding could render it and the plate tree's root was honestly unresolved. This row is that field written
    down once per case: `elements_json` = one matrix row per element [cx, cy, σ_vm, σ_xx, σ_yy, σ_xy, area],
    `nodes_json` = one per node [x, y, u_x, u_y]. A 2-D `field` binding fans `elements_json` into per-element
    cells coloured by σ_vm (column 2) through the binding's colour scale. Provenance travels: the case, the
    material line E/ν came from, the assumption, the element count. Rewritten by `POST /api/tensormath/fem/
    {case}/materialise` (or at seed when the engine can solve the seed case)."""

    plain_words = ('A field state is the result of one solved physics case written down per element or per node, for example '
                   'the stress in each small triangle of a plate, together with where the material numbers came from.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        case: str = '',
        elements_json: str = '[]',
        nodes_json: str = '[]',
        triangles_json: str = '[]',
        n_elements: int = 0,
        n_nodes: int = 0,
        sigma_vm_max: float = 0.0,
        sigma_vm_min: float = 0.0,
        u_max: float = 0.0,
        assumption: str = '',
        material_provenance: str = '',
        columns_json: str = '["cx","cy","sigma_vm","sigma_xx","sigma_yy","sigma_xy","area"]',
        node_columns_json: str = '["x","y","u_x","u_y"]',
        computed_at: str = '',
        provenance: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.case = case  # FEMModelDefinition.name this field was solved from
        self.elements_json = elements_json  # matrix: one row per element (see columns_json)
        self.nodes_json = nodes_json  # matrix: one row per node (see node_columns_json)
        self.triangles_json = triangles_json  # [n_elements, 3] node indices — the mesh, so its edges can be drawn (tt-9)
        self.n_elements = n_elements
        self.n_nodes = n_nodes
        self.sigma_vm_max = sigma_vm_max  # Pa — the field's own range, so a colour domain can be honest
        self.sigma_vm_min = sigma_vm_min
        self.u_max = u_max  # m
        self.assumption = assumption  # plane-stress | plane-strain
        self.material_provenance = material_provenance  # the cited line E/ν came from
        self.columns_json = columns_json
        self.node_columns_json = node_columns_json
        self.computed_at = computed_at
        self.provenance = provenance  # engine + version note
