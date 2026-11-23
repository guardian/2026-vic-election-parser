# Clean early voting data

input_folder <- "data/vec/2026/postalearlyvoting"


# Single-workbook cleaner for Postal And Early Voting Summary Excel reports.
# Install dependencies once: install.packages("readxl")
# 1. Set input_folder and input_filename to the location of your XLSX file.
# 2. Run this entire script in R or RStudio (no command-line arguments needed).
# 3. The cleaned district-level data is saved to cleaned_voting.csv in the same folder.

suppressPackageStartupMessages({
  library(readxl)
})

# EDIT THE FOLDER AND FILENAME to match your computer.
# Forward slashes work on both Windows and macOS.
# input_folder <- "/path/to/folder/containing/xlsx_files"

input_folder <- "data/vec/2026/postalearlyvoting"
output_folder <- "data/lm/2026/postalearlyvoting"
input_filename <- "PostalAndEarlyVotingSummary.xlsx"

if (!dir.exists(input_folder)) {
  stop("Input folder does not exist. Edit input_folder: ", input_folder)
}

input_path <- file.path(input_folder, input_filename)
if (!file.exists(input_path)) {
  stop("Input XLSX file does not exist: ", input_path)
}
if (!grepl("\\.xlsx$", input_filename, ignore.case = TRUE)) {
  stop("Input filename must end in .xlsx: ", input_filename)
}
output_path <- file.path(output_folder, "cleaned_postal_early_voting.csv")

measures <- c(
  "applications_processed_daily", "applications_processed_cumulative",
  "applications_cancelled_daily", "applications_cancelled_cumulative",
  "postal_votes_returned_daily", "postal_votes_returned_cumulative",
  "early_votes_returned_daily", "early_votes_returned_cumulative"
)

parse_date <- function(x) {
  x <- trimws(x)
  result <- as.Date(x, format = "%d/%m/%Y")
  miss <- is.na(result)
  result[miss] <- as.Date(x[miss], format = "%Y-%m-%d")
  result
}

clean_one <- function(path) {
  # Read all original cells as text to avoid mixed date/label column type guessing.
  raw <- as.data.frame(read_excel(path, sheet = 1, col_names = FALSE,
                                  col_types = "text", .name_repair = "unique"),
                       stringsAsFactors = FALSE)
  if (ncol(raw) < 9L) stop("Expected nine columns in ", path)
  raw <- raw[, seq_len(9), drop = FALSE]
  raw[] <- lapply(raw, function(x) { x <- trimws(x); x[is.na(x)] <- ""; x })
  
  header <- which(tolower(raw[[1]]) == "date")
  if (length(header) != 1L) stop("Cannot identify unique Date header in ", path)
  election <- if (nrow(raw) >= 2) raw[[1]][2] else ""
  data <- raw[seq.int(header + 1L, nrow(raw)), , drop = FALSE]
  names(data) <- c("record_label", measures)
  data <- data[nzchar(data$record_label), , drop = FALSE]
  
  dates <- parse_date(data$record_label)
  is_date <- !is.na(dates)
  is_total <- tolower(data$record_label) %in% c("total", "grand total")
  if (!any(is_date)) stop("No daily date rows found in ", path)
  if (any(!is_date & !is_total & !nzchar(data$record_label))) stop("Unexpected empty labels")
  # Each date row begins a block; district rows inherit that date.
  groups <- cumsum(is_date)
  if (any(groups == 0L & !is_total)) stop("District before first date in ", path)
  inherited_date <- rep(as.Date(NA), nrow(data))
  # Index into date rows only; indexing the full dates vector incorrectly assigns NA.
  inherited_date[groups > 0L] <- dates[is_date][match(groups[groups > 0L], groups[is_date])]
  # Totals are separate and never treated as districts.
  convert_number <- function(x, label) {
    x <- gsub(",", "", x, fixed = TRUE)
    empty <- !nzchar(x)
    bad <- !empty & !grepl("^[0-9]+$", x)
    if (any(bad)) stop("Invalid count(s) in ", label, " of ", path)
    y <- suppressWarnings(as.numeric(x))
    y[empty] <- NA_real_
    y
  }
  for (nm in measures) data[[nm]] <- convert_number(data[[nm]], nm)
  if (anyNA(data[!is_total, measures, drop = FALSE]))
    warning("Missing numeric value(s) in ", path)
  
  common <- data.frame(source_file = basename(path), election = election,
                       stringsAsFactors = FALSE)
  common <- common[rep(1L, nrow(data)), , drop = FALSE]
  common$date <- inherited_date
  combined <- cbind(common, data, row.names = NULL)
  district <- combined[!is_date & !is_total, , drop = FALSE]
  names(district)[names(district) == "record_label"] <- "electoral_district"
  statewide <- combined[is_date, , drop = FALSE]
  statewide$record_label <- NULL
  totals <- combined[is_total, , drop = FALSE]
  totals$date <- as.Date(NA)
  names(totals)[names(totals) == "record_label"] <- "total_label"
  
  if (anyNA(district$date))
    stop("District rows with missing inherited dates in ", path)
  duplicate_rows <- duplicated(district[c("date", "electoral_district")]) |
    duplicated(district[c("date", "electoral_district")], fromLast = TRUE)
  if (any(duplicate_rows)) {
    print(district[duplicate_rows, c("date", "electoral_district"), drop = FALSE])
    stop("Duplicate district/date records in ", path)
  }
  counts <- table(district$date)
  if (length(unique(as.integer(counts))) > 1L)
    warning("District count varies by date in ", path)
  district <- district[order(district$date, district$electoral_district), , drop = FALSE]
  rownames(district) <- NULL
  list(district = district, statewide = statewide, totals = totals)
}

# Process exactly one XLSX file (no list.files(), lapply(), or row-binding).
result <- clean_one(input_path)
district <- result$district
statewide <- result$statewide
totals <- result$totals
rownames(district) <- NULL
rownames(statewide) <- NULL
if (nrow(totals)) rownames(totals) <- NULL

# Diagnostic sheet compares daily district sums with reported statewide counts.
checks <- do.call(rbind, lapply(seq_len(nrow(statewide)), function(i) {
  r <- statewide[i, , drop = FALSE]
  s <- district[district$source_file == r$source_file & district$date == r$date, , drop = FALSE]
  if (!nrow(s)) stop("No district rows for a statewide date row")
  data.frame(source_file = r$source_file, date = r$date,
             electoral_districts = nrow(s),
             all_measures_match = all(vapply(measures, function(nm)
               isTRUE(all.equal(sum(s[[nm]]), r[[nm]])), logical(1))),
             stringsAsFactors = FALSE)
}))

write.csv(district, file = output_path, row.names = FALSE, na = "", fileEncoding = "UTF-8")
message("Saved ", nrow(district), " district-date rows from ",
        basename(input_path), " to ", output_path)
message("Daily district sums match statewide: ", sum(checks$all_measures_match),
        "/", nrow(checks), " days.")
