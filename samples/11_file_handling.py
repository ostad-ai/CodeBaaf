# 11 - File Handling
# Writing to and reading from a file.

filename = "demo_file.txt"

# Writing to a file
with open(filename, "w") as file:
    file.write("Hello from CodeBaaf!\n")
    file.write("This is a test file.\n")
print(f"Data written to {filename}.")

# Reading from the file
print("\nReading file content:")
with open(filename, "r") as file:
    content = file.read()
    print(content)