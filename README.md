<img src="/static/favicon.ico" height="150px">

# Origami Terminal
This is a web application for a paper trading portfolio that allows users to buy and sell stocks with a starting fund of $10,000 USD. It uses real-time data from a third-party API. 

![Front page displaying a user's portfolio](/static/images/origamiTerminal-index-1.png)

## Libraries/Technologies Used
Flask, Postgres, Bootstrap, IEX API

## How It Works
`application.py` defines Flask routes to access the Postgres database. There are 2 database schemas, one for `user` and one for `history` (for transactions). `/templates` contain the HTMl/Jinja templates to be rendered. Some helper functions (currency formatting, API look-up...) are defined in `helpers.py`.

## Features
- Look up stock price
- Buy stocks
- Sell stocks
- See transactions history
- User registration
- User athentication
- Change password

## Things to add for fun
- Visualize current portfolio composition
- Create demo user for app demo
- Access historical stock prices
- Visualization of portfolio returns over time + other stats
- Visualization of stock price over time
- Take a look at algo trading libraries
- Jazz up the UI