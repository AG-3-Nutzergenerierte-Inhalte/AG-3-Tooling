#!/bin/bash
#
# This script calculates the total number of lines for each file type in a Git
# repository. It only considers files tracked by Git, respecting .gitignore.
#
# USAGE:
# 1. Place this script in the root of your project directory.
# 2. Make it executable: chmod +x count_lines_by_type.sh
# 3. Run it: ./count_lines_by_type.sh

# Check for required commands
if ! command -v git &> /dev/null; then
    echo "Error: 'git' command not found. This script must be run in a Git repository." >&2
    exit 1
fi

# Use an associative array to store line counts for each file extension.
# This requires Bash 4.0+.
declare -A line_counts

echo "🔍 Analyzing tracked files and counting lines..."

# Use 'git ls-files' to get a list of all files tracked by git.
# Pipe this list into a loop to process each file.
# We use process substitution (< <(command)) instead of a pipe (|) to avoid
# running the while loop in a subshell. This ensures that the 'line_counts'
# associative array is modified in the current shell, not a child process.
while read -r filename; do
    # Skip directories and non-existent files
    if [ ! -f "$filename" ]; then
        continue
    fi

    # Determine the file extension
    extension="${filename##*.}"

    # If a file has no extension (e.g., 'Makefile', 'Dockerfile'),
    # or if the name is the extension (e.g. '.gitignore'), group them.
    if [[ "$extension" == "$filename" ]] || [[ -z "$extension" ]]; then
        extension="(no extension)"
    fi

    # Count the lines in the file and add to the corresponding total.
    # The '<' redirects file content to wc's stdin, which makes its output just the line number.
    lines=$(wc -l < "$filename")

    # Add the line count to our associative array.
    # The parameter expansion ${line_counts[$extension]:-0} provides a default of 0.
    ((line_counts["$extension"] = ${line_counts[$extension]:-0} + lines))

done < <(git ls-files)

echo ""
echo "📊 Line Count Statistics per File Type:"
echo "+------------------+-----------------+"
printf "| %-16s | %-15s |\n" "File Type" "Total Lines"
echo "+------------------+-----------------+"

# Print the results sorted by line count in descending order.
# We process the array, sort it numerically, and then format it with printf.
for ext in "${!line_counts[@]}"; do
    echo "$ext ${line_counts[$ext]}"
done | sort -k2 -nr | while read -r ext lines; do
    printf "| %-16s | %-15s |\n" "$ext" "$lines"
done

echo "+------------------+-----------------+"

# Calculate and print the grand total
total_lines=0
for lines in "${line_counts[@]}"; do
    ((total_lines += lines))
done
printf "| %-16s | %-15s |\n" "Total" "$total_lines"
echo "+------------------+-----------------+"

echo ""
echo "✅ Analysis complete."
