# The description of a table for its alt text: how many rows and columns and the columns' names; the HTML table
# carries the cells themselves. Mirrors the Python package's charts/table_alt.py.

# "Table. 5 rows and 4 columns: Group, n, Median and 1 more."; without a title of its own the figure is titled
# "Table" already, so the kind is left out. As Python's table_description().
table_description <- function(spec, titled) {
  size <- word("table_size", rows = swimlanes_counted(length(spec$rows), "rows_one", "rows_many"),
               columns = swimlanes_counted(length(spec$header), "columns_one", "columns_many"),
               names = alt_named(spec$header))
  if (titled) alt_described("kind_table", size) else size
}
