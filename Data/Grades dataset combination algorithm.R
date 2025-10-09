library(readxl)
library(dplyr)
library(stringr)
library(tidyr)
library(janitor)
library(purrr)

# ---------- 1) Build dictionaries from UFM ----------
ufm <- read_excel("DATA_UFM.xlsx") %>% clean_names()

titles_vec <- ufm$titel %>% unique() %>% str_squish() %>% discard(is.na)
cities_vec <- ufm$instkommunetx %>% unique() %>% str_squish() %>% discard(is.na)

# regex-safe alternation, longest-first (so we match "Erhvervsøkonomi, HA" before "Erhvervsøkonomi")
rx_alt <- function(x) {
  x <- x[order(nchar(x), decreasing = TRUE)]
  x <- str_replace_all(x, "([\\\\.^$|?*+()\\[\\]{}])", "\\\\\\1")
  paste(x, collapse = "|")
}
titles_alt <- rx_alt(titles_vec)
cities_alt <- rx_alt(cities_vec)

# ---------- 2) Helpers for normalization ----------
normalize_str  <- function(x) str_to_lower(str_squish(x))

normalize_city <- function(x) {
  x <- normalize_str(x)
  # København variants (Ø/N/V/S/K/NV/SV, etc.) -> "københavn"
  x <- ifelse(str_detect(x, "^københavn\\b"), "københavn", x)
  # Århus -> aarhus
  x <- str_replace(x, "^århus$", "aarhus")
  # Lyngby variants -> lyngby-taarbæk
  x <- ifelse(str_detect(x, "\\bkgs\\.?\\s*lyngby\\b|\\bkongens lyngby\\b|\\blyngby\\b"),
              "lyngby-taarbæk", x)
  x
}

# ---------- 3) Parse the grades sheet using the dictionaries ----------
grades <- read_excel("Adgangskvotienter - videregående uddannelser.xlsx") %>% clean_names()
text_col <- names(grades)[2]  # <- change if your mixed text is another column

grades_parsed <- grades %>%
  mutate(
    txt = .data[[text_col]] %>% str_replace_all("[\\r\\n]+", " ") %>% str_squish(),
    # drop anything after "Studiestart: ..."
    txt = str_remove(txt, "(?i)studiestart\\s*:.*$"),

    # Title: first match of ANY UFM title anywhere in the string
    title = str_match(txt, regex(paste0("(", titles_alt, ")"), ignore_case = TRUE))[,2],

    # City: prefer canonical rules first, else first match of known municipality
    By = case_when(
      str_detect(txt, "(?i)\\bkøbenhavn\\b") ~ "København",
      str_detect(txt, "(?i)\\bårhus\\b")     ~ "Aarhus",
      str_detect(txt, "(?i)\\bkgs\\.?\\s*lyngby\\b|\\bkongens lyngby\\b|\\blyngby\\b") ~ "Lyngby-Taarbæk",
      TRUE ~ str_match(txt, regex(paste0("\\b(", cities_alt, ")\\b"), ignore_case = TRUE))[,2]
    )
  ) %>%
  # Fallback: if either is still NA, take the simple comma split as a last resort
  mutate(
    title = coalesce(title, str_split_fixed(txt, "\\s*,\\s*", 3)[,1]),
    By    = coalesce(By,    str_split_fixed(txt, "\\s*,\\s*", 3)[,2])
  ) %>%
  mutate(
    title_std = normalize_str(title),
    by_std    = normalize_city(By)
  )

# ---------- 4) Prepare UFM keys and JOIN ----------
ufm_key <- ufm %>%
  mutate(
    title_std = normalize_str(titel),
    by_std    = normalize_city(instkommunetx)
  )

grade_cols <- setdiff(names(grades_parsed), c("txt","title_std","by_std"))
DATA_UFM_combined <- ufm_key %>%
  left_join(select(grades_parsed, title_std, by_std, all_of(grade_cols)),
            by = c("title_std","by_std")) %>%
  select(-title_std, -by_std)

# ---------- 5) Diagnostics (what didn’t match?) ----------
not_matched <- anti_join(ufm_key, grades_parsed, by = c("title_std","by_std"))
nrow(not_matched); head(not_matched)

dup_keys <- grades_parsed %>% count(title_std, by_std) %>% filter(n > 1)
dup_keys

library(writexl)

# Save the merged table to an Excel file in your working folder
write_xlsx(DATA_UFM_combined, "DATA_UFM_combined.xlsx")
