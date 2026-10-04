# main component of the C3 template (sc-3): the variant's app (app.c), the common layer, the trace ring.
idf_component_register(SRCS "app.c" "polari_c3.c" "polari_trace.c"
                       INCLUDE_DIRS "."
                       REQUIRES esp_driver_uart esp_partition esp_timer freertos)
