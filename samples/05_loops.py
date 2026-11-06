# 05 - Loops
# Repeating actions without writing the same code.

print("--- For Loop ---")
# Iterating over a sequence
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(f"I love {fruit}!")

print("\n--- While Loop ---")
# Repeating while a condition is true
countdown = 5
while countdown > 0:
    print(f"Countdown: {countdown}")
    countdown -= 1 # Decrease by 1
print("Blast off!")