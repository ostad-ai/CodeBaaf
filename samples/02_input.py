# 02 - User Input
# How to get data from the user via the terminal.

print("Welcome to the Input Test!")

# The input() function pauses the program and waits for the user to type.
name = input("What is your name? ")
age = input("How old are you? ")

# Printing the collected data
print(f"\nNice to meet you, {name}!")
# Note: input() always returns a string, so we convert age to an integer.
print(f"Next year, you will be {int(age) + 1} years old.")