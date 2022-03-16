import os
import psycopg2
import psycopg2.extras
from decimal import Decimal
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

if __name__ == "__main__":
    app.run()

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
uri = os.getenv("DATABASE_URL")
conn = psycopg2.connect(uri)
db = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user = session["user_id"]

    # Query database for stocks owned
    query = '''
        SELECT symbol, SUM(shares) AS shares
        FROM history
        GROUP BY symbol,
        id HAVING id = %s AND SUM(shares) > 0
    '''
    db.execute(query, (user,))
    stocks = db.fetchall()

    # Store cash value
    db.execute("SELECT cash FROM users WHERE id = %s", (user,))
    row = db.fetchall()
    balance = row[0]["cash"]
    sum = balance

    # Index without stocks bought
    if len(stocks) == 0:
        return render_template("index.html", balance=balance, sum=sum)

    print(stocks)

    # Use lookup to find price of all stocks
    for stock in stocks:

        # Calculate current price
        quote = lookup(stock["symbol"])
        price = quote['price']
        total = price * int(stock["shares"])

        print(stocks)

        # Incorporate price into dict
        stock["price"] = price
        stock["total"] = total

        sum += Decimal(total)

    return render_template("index.html", stocks=stocks, balance=balance, sum=sum)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # POST: buy stock
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        if shares.isnumeric() == False:
            return apology("Share number must be a postive integer")

        elif isinstance(shares, float) or float(shares) < 0:
            return apology("Share number must be a postive integer")

        shares = int(shares)

        if lookup(symbol):

            quote = lookup(symbol)
            cost = shares * quote["price"]

            # Save user id
            user = session["user_id"]
            db.execute("SELECT cash FROM users WHERE id = %s", (user,))
            row = db.fetchall()

            # Check cash reserves
            if row[0]["cash"] < cost:
                return apology("Not enough cash")

            else:
                # New cash total
                balance = row[0]["cash"] - Decimal(cost)

                # Decrease user cash
                db.execute("UPDATE users SET cash=%s WHERE id=%s", (balance, user,))

                # Insert transaction into table
                db.execute("INSERT INTO history (symbol, shares, price, date, id) VALUES(%s, %s, %s, CURRENT_TIMESTAMP, %s)",
                           (symbol, shares, quote["price"], user,))

                conn.commit()

                return redirect("/")

        elif shares < 1:
            return apology("Shares must be at least 1")
        else:
            return apology("Check the symbol")

    # GET: display form
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user = session["user_id"]

    db.execute("SELECT * FROM history WHERE id = %s", (user,))
    stocks = db.fetchall()

    return render_template("history.html", stocks=stocks)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        query = '''
            SELECT * FROM users WHERE username = %s
        '''
        db.execute(query, (request.form.get("username"),) )
        rows = db.fetchall()
        print(rows)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # POST: Retrieve stock price
    if request.method == "POST":
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("Must supply valid symbol")

        elif not lookup(symbol):
            return apology("Must supply valid symbol")

        quote = lookup(symbol)
        return render_template("quoted.html", quote=quote)

    # GET: Display form
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        query = '''
            SELECT * FROM users WHERE username = %s
        '''

        db.execute(query, (username,))
        rows = db.fetchall()
        
        # Ensure the username was submitted
        if not username:
            return apology("must provide username", 400)

        # Ensure the username is not taken
        elif len(rows) != 0:
            return apology("username taken", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        # Ensure confirmation password was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password confirmation", 400)

        # Ensure passwords match
        elif not password == confirmation:
            return apology("passwords must match", 400)

        else:
            # Generate the hash of the password
            hash = generate_password_hash(
                password, method="pbkdf2:sha256", salt_length=16
            )
            # Insert the new user
            db.execute("INSERT INTO users (username, hash) VALUES (%s, %s) ", (username, hash,))

            conn.commit()

            # Redirect user to home page
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":

        user = session["user_id"]
        password = request.form.get("password")
        newPassword = request.form.get("newPassword")
        confirmation = request.form.get("confirmation")

        # Query database for username
        db.execute("SELECT * FROM users WHERE id = %s", (user,))
        rows = db.fetchall()

        # Ensure all fields entered
        if not password or not newPassword or not confirmation:
            return apology("must fill in all fields", 400)

        # Ensure username exists and password is correct
        elif not check_password_hash(rows[0]["hash"], password):
            return apology("invalid password", 403)

        # Ensure passwords match
        elif not newPassword == confirmation:
            return apology("passwords must match", 400)

        else:
            # Generate the hash of the password
            hash = generate_password_hash(
                newPassword, method="pbkdf2:sha256", salt_length=16
            )

            # Update password
            db.execute("UPDATE users SET hash = %s WHERE id = %s", (hash, user,))
            conn.commit()

            return redirect("/")

    else:
        return render_template("settings.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Find user stocks
    user = session["user_id"]
    query = '''
        SELECT symbol, SUM(shares) 
        FROM history 
        GROUP BY symbol, id
        HAVING id = %s AND SUM(shares) > 0
    '''
    db.execute(query, (user,))

    stocks = db.fetchall()

    if request.method == "POST":
        # POST: Update user cash
        symbol = str(request.form.get("symbol"))
        shares = int(request.form.get("shares"))

        query = '''
            SELECT SUM(shares) AS shares 
            FROM history 
            GROUP BY symbol, id
            HAVING id = %s AND symbol = %s
        '''
        db.execute(query, (user, symbol,))

        items = db.fetchall()

        owned = items[0]["shares"]

        if len(items) != 1:
            return apology("Wrong symbol?")

        elif shares > owned:
            return apology("Not enough shares")

        # Sell stock
        quote = lookup(symbol)
        sale = quote["price"] * shares
        shares = -abs(shares)
        owned = owned + shares

        # Find new balance
        db.execute("SELECT cash FROM users WHERE id = %s", (user,))
        row = db.fetchall()

        balance = Decimal(sale) + row[0]["cash"]

        # Update user cash and stocks
        db.execute("UPDATE users SET cash=%s WHERE id=%s", (balance, user,))
        conn.commit()

        # Update tranasction history
        db.execute("INSERT INTO history (symbol, shares, price, date, id) VALUES(%s, %s, %s, CURRENT_TIMESTAMP, %s)",
                   (symbol, shares, quote["price"], user,))
        return redirect("/")

    # GET: Display form to sell stock
    else:
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)