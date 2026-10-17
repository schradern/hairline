withr::local_envvar(HAIRLINE_HOST_CONTEXT = NA, .local_envir = teardown_env())
withr::local_options(device = function(...) ragg::agg_png(tempfile(fileext = ".png"), ...),
                     .local_envir = teardown_env())
