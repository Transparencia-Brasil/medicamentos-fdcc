# Este script só entra em ação após renderizar um arquivo qmd, funciona em conjunto com __ quarto.yml
# Após rodar um arquivo qmd, este script irá transferir arquivos HTML para a pasta `docs/`

out_dir <- fs::path_tidy(Sys.getenv("QUARTO_PROJECT_OUTPUT_DIR"))
# cat("\nout_dir:\n", out_dir, "\n")

out_files <- fs::path_tidy(strsplit(Sys.getenv("QUARTO_PROJECT_OUTPUT_FILES"), "\n")[[1]])
cat("\nout_files:\n", paste(out_files, collapse = ", "), "\n")

# "notebook_files" for "notebook.html"
assets <- out_files |>
  grep("\\.html$", x = _, value = TRUE) |>
  gsub("\\.html$", "_files", x = _)

assets <- assets[fs::dir_exists(assets)]
# cat("\nassets:\n", paste(assets, collapse = ", "), "\n")

dest <- fs::path(out_dir, fs::path_file(assets))
fs::dir_copy(assets, dest, overwrite = TRUE)
cat("\nArquivos copiados com sucesso!\n")

# atualiza file-structure.json
files <- list.files(
  path = "docs",
  pattern = "html$",
  full.names = TRUE,
  recursive = TRUE
)
# cat("\nfiles:\n", paste(files, collapse = ",\n"), "\n")

data.frame(subdir = gsub("^docs\\/", "", dirname(files)), path = gsub("^docs\\/", "", files)) |>
  dplyr::mutate(subdir = ifelse(subdir == "docs", ".", subdir)) |>
  dplyr::group_nest(subdir) |>
  tibble::deframe() |>
  jsonlite::toJSON(pretty = TRUE) |>
  writeLines("docs/file-structure.json")

cat("\nArquivo file-structure.json atualizado com sucesso!\n")
# cat("\ndirname(files)\n", paste(dirname(files), collapse = "\n"), "\n")
# cat("\nsubdir\n", paste(gsub("^docs\\/", "", dirname(files)), collapse = "\n"), "\n")
# cat("\npath\n", paste(gsub("^docs\\/", "", files), collapse = "\n"), "\n")
