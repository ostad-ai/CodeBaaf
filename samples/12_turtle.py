# 12 - Turtle Graphics
# A fun way to draw using Python's built-in turtle module.

import turtle

# Setup the screen
screen = turtle.Screen()
screen.title("CodeBaaf Turtle")
screen.bgcolor("black")

# Setup the turtle
t = turtle.Turtle()
t.color("cyan")
t.pensize(2)
t.speed(0) # Fastest drawing speed

# Draw a spiral pattern
for i in range(100):
    t.forward(i * 2)
    t.right(45)

# Keep the window open until clicked
turtle.done()