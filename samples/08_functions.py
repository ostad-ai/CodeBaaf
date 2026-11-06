# 08 - Functions
# Writing reusable blocks of code.

# Defining a function
def greet(name):
    return f"Hello, {name}! Welcome to CodeBaaf."

# Calling the function
message = greet("Bahram")
print(message)

# Function with default arguments
def add_numbers(a, b=10):
    return a + b

print(f"Adding 5 and 10: {add_numbers(5)}")
print(f"Adding 5 and 20: {add_numbers(5, 20)}")