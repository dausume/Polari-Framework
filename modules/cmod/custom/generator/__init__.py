"""
@module cmod.custom.generator

fgm-0 (FIRMWARE_GENERATION_MODULE_PLAN.md §5/§7.7): the Jinja2 foundation. Generated C is RENDERED from templates
(modules/cmod/custom/templates/avr/) over a TYPED context; nothing reaches a template as free-form text:

  env.py      the Environment (StrictUndefined, keep_trailing_newline, trim/lstrip blocks) + template provenance (sha256)
  filters.py  c_ident / c_type / c_expr / c_int / c_hex / c_block — the only ways a value becomes C
  context.py  the graph glue's context (what glue.context()/render_files() hold today, normalized into statements)
  pin_context.py  pin_config.h/.c's context (the register-setting plan, normalized)
"""
