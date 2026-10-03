from flask import Flask, render_template, request, redirect, session
from db import get_connection
from flask import jsonify

app = Flask(__name__)
app.secret_key = "ecommerce_secret_key"

@app.route("/")
def home():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.product_id, p.product_name, p.description, p.price,
               p.image, p.discount, p.rating, s.seller_name, i.stock_quantity
        FROM Products p
        JOIN Sellers s ON p.seller_id = s.seller_id
        JOIN Inventory i ON p.product_id = i.product_id
    """)
    products = cursor.fetchall()

    cursor.execute("SELECT * FROM Categories")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        search=""
    )
@app.route("/products")
def products():

    search = request.args.get("search", "")
    category = request.args.get("category", "")
    max_price = request.args.get("max_price", "")
    sort = request.args.get("sort", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            p.product_id,
            p.product_name,
            p.description,
            p.price,
            p.image,
            p.discount,
            p.rating,
            s.seller_name,
            i.stock_quantity,
            c.category_name

        FROM Products p

        JOIN Sellers s
        ON p.seller_id = s.seller_id

        JOIN Inventory i
        ON p.product_id = i.product_id

        JOIN Categories c
        ON p.category_id = c.category_id

        WHERE p.product_name LIKE %s
    """

    values = [f"%{search}%"]

    if category:
        query += " AND c.category_name = %s"
        values.append(category)

    if max_price:
        query += " AND p.price <= %s"
        values.append(max_price)

    if sort == "low_to_high":
        query += " ORDER BY p.price ASC"

    elif sort == "high_to_low":
        query += " ORDER BY p.price DESC"

    elif sort == "rating":
        query += " ORDER BY p.rating DESC"

    else:
        query += " ORDER BY p.product_id DESC"

    cursor.execute(query, tuple(values))

    products = cursor.fetchall()

    cursor.execute("SELECT * FROM Categories")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        search=search
    )
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = password

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Users(name, email, password)
            VALUES(%s, %s, %s)
        """, (
            name,
            email,
            hashed_password
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and user["password"] == password:
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]

            cursor.execute("SELECT * FROM Cart WHERE user_id=%s", (user["user_id"],))
            cart = cursor.fetchone()

            if not cart:
                cursor.execute("INSERT INTO Cart(user_id) VALUES(%s)", (user["user_id"],))
                conn.commit()

            cursor.close()
            conn.close()

            return redirect("/")

        cursor.close()
        conn.close()
        return "Invalid Email or Password"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Cart WHERE user_id=%s", (session["user_id"],))
    cart = cursor.fetchone()

    if not cart:
        cursor.execute("INSERT INTO Cart(user_id) VALUES(%s)", (session["user_id"],))
        conn.commit()

        cursor.execute("SELECT * FROM Cart WHERE user_id=%s", (session["user_id"],))
        cart = cursor.fetchone()

    cart_id = cart["cart_id"]

    cursor.execute("""
        SELECT * FROM CartItems
        WHERE cart_id=%s AND product_id=%s
    """, (cart_id, product_id))

    item = cursor.fetchone()

    if item:
        cursor.execute("""
            UPDATE CartItems
            SET quantity = quantity + 1
            WHERE cart_id=%s AND product_id=%s
        """, (cart_id, product_id))
    else:
        cursor.execute("""
            INSERT INTO CartItems(cart_id, product_id, quantity)
            VALUES(%s, %s, 1)
        """, (cart_id, product_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/cart")

@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT cart_id FROM Cart WHERE user_id=%s",
        (session["user_id"],)
    )

    cart = cursor.fetchone()

    if not cart:
        cursor.close()
        conn.close()
        return render_template(
            "cart.html",
            cart_items=[],
            total=0
        )

    cursor.execute("""
        SELECT 
            ci.cart_item_id,
            ci.quantity,
            p.product_name,
            p.description,
            p.price,
            p.image,
            p.discount
        FROM CartItems ci
        JOIN Products p
        ON ci.product_id = p.product_id
        WHERE ci.cart_id=%s
    """, (cart["cart_id"],))

    cart_items = cursor.fetchall()

    total = 0

    for item in cart_items:
        if item["discount"] and item["discount"] > 0:
            final_price = item["price"] - (
                item["price"] * item["discount"] / 100
            )
        else:
            final_price = item["price"]

        total += final_price * item["quantity"]

    cursor.close()
    conn.close()

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=round(total, 2)
    )
@app.route("/remove_cart_item/<int:cart_item_id>")
@app.route("/remove_from_cart/<int:cart_item_id>")
def remove_cart_item(cart_item_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # Delete selected cart item
    cursor.execute("""
        DELETE FROM CartItems
        WHERE cart_item_id=%s
    """, (cart_item_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/cart")
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT cart_id FROM Cart WHERE user_id=%s", (user_id,))
    cart = cursor.fetchone()

    if not cart:
        cursor.close()
        conn.close()
        return redirect("/cart")

    cursor.execute("""
        SELECT 
            ci.quantity,
            p.product_id,
            p.price
        FROM CartItems ci
        JOIN Products p ON ci.product_id = p.product_id
        WHERE ci.cart_id=%s
    """, (cart["cart_id"],))

    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close()
        conn.close()
        return redirect("/cart")

    # STOCK VALIDATION
    for item in cart_items:
        cursor.execute("""
            SELECT stock_quantity
            FROM Inventory
            WHERE product_id=%s
        """, (item["product_id"],))

        stock = cursor.fetchone()

        if not stock or stock["stock_quantity"] < item["quantity"]:
            cursor.close()
            conn.close()
            return "Not enough stock available for one or more products."

    total = 0
    for item in cart_items:
        total += item["price"] * item["quantity"]

    if request.method == "POST":
        payment_method = request.form["payment_method"]

        cursor.execute("""
            INSERT INTO Orders(user_id, order_date, total_amount, status)
            VALUES(%s, CURDATE(), %s, %s)
        """, (user_id, total, "Placed"))

        order_id = cursor.lastrowid

        for item in cart_items:
            cursor.execute("""
                INSERT INTO OrderItems(order_id, product_id, quantity, price)
                VALUES(%s, %s, %s, %s)
            """, (
                order_id,
                item["product_id"],
                item["quantity"],
                item["price"]
            ))

            cursor.execute("""
                UPDATE Inventory
                SET stock_quantity = stock_quantity - %s
                WHERE product_id = %s
            """, (item["quantity"], item["product_id"]))

        cursor.execute("""
            INSERT INTO Payments(order_id, payment_method, payment_status, payment_date)
            VALUES(%s, %s, %s, CURDATE())
        """, (order_id, payment_method, "Success"))

        cursor.execute("""
            INSERT INTO OrderTracking(order_id, tracking_status, tracking_date)
            VALUES(%s, %s, CURDATE())
        """, (order_id, "Order Placed"))

        cursor.execute("""
            DELETE FROM CartItems
            WHERE cart_id=%s
        """, (cart["cart_id"],))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/orders")

    cursor.close()
    conn.close()

    return render_template("checkout.html", total=total)

@app.route("/orders")
def orders():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            o.order_id,
            o.total_amount,
            o.status,
            o.order_date,
            p.payment_method,
            p.payment_status,

            (
                SELECT ot.tracking_status
                FROM OrderTracking ot
                WHERE ot.order_id = o.order_id
                ORDER BY ot.tracking_id DESC
                LIMIT 1
            ) AS tracking_status,

            (
                SELECT pr.product_name
                FROM OrderItems oi
                JOIN Products pr ON oi.product_id = pr.product_id
                WHERE oi.order_id = o.order_id
                LIMIT 1
            ) AS product_name,

            (
                SELECT pr.image
                FROM OrderItems oi
                JOIN Products pr ON oi.product_id = pr.product_id
                WHERE oi.order_id = o.order_id
                LIMIT 1
            ) AS image

        FROM Orders o
        JOIN Payments p ON o.order_id = p.order_id
        WHERE o.user_id = %s
        ORDER BY o.order_id DESC
    """, (session["user_id"],))

    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("orders.html", orders=orders)
@app.route("/admin")
def admin():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS count FROM Users")
    users_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM Products")
    products_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM Orders")
    orders_count = cursor.fetchone()["count"]

    cursor.execute("SELECT IFNULL(SUM(total_amount),0) AS total FROM Orders")
    total_sales = cursor.fetchone()["total"]

    cursor.execute("SELECT * FROM Categories")
    categories = cursor.fetchall()

    cursor.execute("SELECT * FROM Sellers")
    sellers = cursor.fetchall()

    cursor.execute("""
        SELECT 
            p.product_id,
            p.product_name,
            p.price,
            p.image,
            i.stock_quantity
        FROM Products p
        JOIN Inventory i ON p.product_id = i.product_id
        ORDER BY p.product_id DESC
    """)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin.html",
        users_count=users_count,
        products_count=products_count,
        orders_count=orders_count,
        total_sales=total_sales,
        categories=categories,
        sellers=sellers,
        products=products
    )
@app.route("/admin/add_product", methods=["POST"])
def add_product():

    product_name = request.form["product_name"]
    description = request.form["description"]
    price = request.form["price"]
    image = request.form["image"]
    discount = request.form["discount"]
    stock_quantity = request.form["stock_quantity"]
    category_id = request.form["category_id"]
    seller_id = request.form["seller_id"]

    conn = get_connection()
    cursor = conn.cursor()

    # Insert into Products table
    cursor.execute("""
        INSERT INTO Products(
            product_name,
            description,
            price,
            image,
            discount,
            seller_id,
            category_id
        )
        VALUES(%s, %s, %s, %s, %s, %s, %s)
    """, (
        product_name,
        description,
        price,
        image,
        discount,
        seller_id,
        category_id
    ))

    # Get new product id
    product_id = cursor.lastrowid

    # Insert stock into Inventory table
    cursor.execute("""
        INSERT INTO Inventory(
            product_id,
            stock_quantity
        )
        VALUES(%s, %s)
    """, (
        product_id,
        stock_quantity
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin")

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            p.product_id,
            p.product_name,
            p.description,
            p.price,
            p.image,
            p.discount,
            p.rating,
            s.seller_name,
            i.stock_quantity
        FROM Products p
        JOIN Sellers s ON p.seller_id = s.seller_id
        JOIN Inventory i ON p.product_id = i.product_id
        WHERE p.product_id = %s
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return redirect("/")

    cursor.execute("""
        SELECT 
            r.rating,
            r.comment,
            u.name
        FROM Reviews r
        JOIN Users u ON r.user_id = u.user_id
        WHERE r.product_id = %s
        ORDER BY r.review_id DESC
    """, (product_id,))

    reviews = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "product_detail.html",
        product=product,
        reviews=reviews
    )
@app.route("/add_review/<int:product_id>", methods=["POST"])
def add_review(product_id):
    if "user_id" not in session:
        return redirect("/login")

    rating = request.form["rating"]
    comment = request.form["comment"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Reviews(user_id, product_id, rating, comment)
        VALUES(%s, %s, %s, %s)
    """, (session["user_id"], product_id, rating, comment))

    cursor.execute("""
        UPDATE Products
        SET rating = (
            SELECT AVG(rating)
            FROM Reviews
            WHERE product_id=%s
        )
        WHERE product_id=%s
    """, (product_id, product_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(f"/product/{product_id}")
@app.route("/seller_register", methods=["GET", "POST"])
def seller_register():
    if request.method == "POST":
        seller_name = request.form["seller_name"]
        email = request.form["email"]
        phone = request.form["phone"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Sellers(seller_name, email, phone)
            VALUES(%s, %s, %s)
        """, (seller_name, email, phone))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/seller_login")

    return render_template("seller_register.html")
@app.route("/buynow/<int:product_id>", methods=["GET", "POST"])
def buynow(product_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            p.product_id,
            p.product_name,
            p.description,
            p.price,
            p.image,
            p.discount,
            i.stock_quantity
        FROM Products p
        LEFT JOIN Inventory i
            ON p.product_id = i.product_id
        WHERE p.product_id = %s
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "Product not found", 404

    if request.method == "POST":

        quantity = int(request.form.get("quantity", 1))

        if product["stock_quantity"] is None:
            cursor.close()
            conn.close()
            return "Product inventory not found", 400

        if quantity <= 0:
            cursor.close()
            conn.close()
            return "Invalid quantity", 400

        if quantity > product["stock_quantity"]:
            cursor.close()
            conn.close()
            return "Not enough stock", 400

        if product["discount"] and product["discount"] > 0:
            discounted_price = (
                product["price"]
                - (product["price"] * product["discount"] / 100)
            )
        else:
            discounted_price = product["price"]

        total = discounted_price * quantity

        session["buy_now_product_id"] = product_id
        session["buy_now_quantity"] = quantity
        session["buy_now_total"] = float(total)

        cursor.close()
        conn.close()

        return redirect("/checkout")

    cursor.close()
    conn.close()

    return render_template(
        "buy_now.html",
        product=product
    )
@app.route("/seller_login", methods=["GET", "POST"])
def seller_login():
    if request.method == "POST":
        email = request.form["email"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Sellers WHERE email=%s", (email,))
        seller = cursor.fetchone()

        cursor.close()
        conn.close()

        if seller:
            session["seller_id"] = seller["seller_id"]
            session["seller_name"] = seller["seller_name"]
            return redirect("/seller_dashboard")

        return "Seller Not Found"

    return render_template("seller_login.html")


@app.route("/seller_dashboard")
def seller_dashboard():
    if "seller_id" not in session:
        return redirect("/seller_login")

    seller_id = session["seller_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM Products
        WHERE seller_id=%s
    """, (seller_id,))
    total_products = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM OrderItems oi
        JOIN Products p ON oi.product_id = p.product_id
        WHERE p.seller_id=%s
    """, (seller_id,))
    total_orders = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT IFNULL(SUM(oi.price * oi.quantity),0) AS revenue
        FROM OrderItems oi
        JOIN Products p ON oi.product_id = p.product_id
        WHERE p.seller_id=%s
    """, (seller_id,))
    total_revenue = cursor.fetchone()["revenue"]

    cursor.execute("""
        SELECT 
            p.product_name,
            p.price,
            p.image,
            p.rating,
            i.stock_quantity
        FROM Products p
        JOIN Inventory i ON p.product_id = i.product_id
        WHERE p.seller_id=%s
    """, (seller_id,))
    products = cursor.fetchall()

    cursor.execute("SELECT * FROM Categories")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "seller_dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        products=products,
        categories=categories
    )


@app.route("/seller/add_product", methods=["POST"])
def seller_add_product():
    if "seller_id" not in session:
        return redirect("/seller_login")

    product_name = request.form["product_name"]
    description = request.form["description"]
    price = request.form["price"]
    image = request.form["image"]
    discount = request.form["discount"]
    stock_quantity = request.form["stock_quantity"]
    category_id = request.form["category_id"]
    seller_id = session["seller_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Products
        (product_name, description, price, category_id, seller_id, image, discount, rating)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        product_name,
        description,
        price,
        category_id,
        seller_id,
        image,
        discount,
        4.0
    ))

    product_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO Inventory(product_id, stock_quantity)
        VALUES(%s, %s)
    """, (product_id, stock_quantity))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/seller_dashboard")


@app.route("/seller_logout")
def seller_logout():
    session.pop("seller_id", None)
    session.pop("seller_name", None)
    return redirect("/")

@app.route("/admin/orders")
def admin_orders():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            o.order_id,
            o.total_amount,
            o.status,
            o.order_date,
            u.name
        FROM Orders o
        JOIN Users u ON o.user_id = u.user_id
        ORDER BY o.order_id DESC
    """)

    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_orders.html", orders=orders)


@app.route("/admin/update_order/<int:order_id>", methods=["POST"])
def update_order(order_id):
    status = request.form["status"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Orders
        SET status=%s
        WHERE order_id=%s
    """, (status, order_id))

    cursor.execute("""
        INSERT INTO OrderTracking(order_id, tracking_status, tracking_date)
        VALUES(%s, %s, CURDATE())
    """, (order_id, status))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin/orders")

@app.route("/add_to_wishlist/<int:product_id>")
def add_to_wishlist(product_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT IGNORE INTO Wishlist(user_id, product_id)
        VALUES(%s, %s)
    """, (session["user_id"], product_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/wishlist")


@app.route("/wishlist")
def wishlist():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            w.wishlist_id,
            p.product_id,
            p.product_name,
            p.price,
            p.image,
            p.discount,
            p.rating
        FROM Wishlist w
        JOIN Products p ON w.product_id = p.product_id
        WHERE w.user_id=%s
        ORDER BY w.wishlist_id DESC
    """, (session["user_id"],))

    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("wishlist.html", items=items)


@app.route("/remove_wishlist/<int:wishlist_id>")
def remove_wishlist(wishlist_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Wishlist
        WHERE wishlist_id=%s AND user_id=%s
    """, (wishlist_id, session["user_id"]))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/wishlist")

@app.route("/add_category", methods=["POST"])
def add_category():

    category_name = request.form["category_name"]
    image = request.form["image"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Categories(category_name, image)
        VALUES(%s, %s)
    """, (category_name, image))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin")
@app.route("/delete_product/<int:product_id>")
def delete_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Wishlist WHERE product_id=%s", (product_id,))
    cursor.execute("DELETE FROM Reviews WHERE product_id=%s", (product_id,))
    cursor.execute("DELETE FROM CartItems WHERE product_id=%s", (product_id,))
    cursor.execute("DELETE FROM OrderItems WHERE product_id=%s", (product_id,))
    cursor.execute("DELETE FROM Inventory WHERE product_id=%s", (product_id,))
    cursor.execute("DELETE FROM Products WHERE product_id=%s", (product_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/admin")
@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        product_name = request.form["product_name"]
        description = request.form["description"]
        price = request.form["price"]
        image = request.form["image"]
        discount = request.form["discount"]
        stock_quantity = request.form["stock_quantity"]

        cursor.execute("""
            UPDATE Products
            SET product_name=%s, description=%s, price=%s, image=%s, discount=%s
            WHERE product_id=%s
        """, (product_name, description, price, image, discount, product_id))

        cursor.execute("""
            UPDATE Inventory
            SET stock_quantity=%s
            WHERE product_id=%s
        """, (stock_quantity, product_id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/admin")

    cursor.execute("""
        SELECT p.*, i.stock_quantity
        FROM Products p
        JOIN Inventory i ON p.product_id = i.product_id
        WHERE p.product_id=%s
    """, (product_id,))

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("edit_product.html", product=product)

@app.route("/delete_category/<int:category_id>")
def delete_category(category_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM Products
        WHERE category_id=%s
    """, (category_id,))

    product_count = cursor.fetchone()["count"]

    if product_count > 0:
        cursor.close()
        conn.close()
        return "Cannot delete category. Products exist in this category."

    cursor.execute("""
        DELETE FROM Categories
        WHERE category_id=%s
    """, (category_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/admin")



@app.route("/edit_category/<int:category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        category_name = request.form["category_name"]
        image = request.form["image"]

        cursor.execute("""
            UPDATE Categories
            SET category_name=%s, image=%s
            WHERE category_id=%s
        """, (category_name, image, category_id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/admin")

    cursor.execute("""
        SELECT * FROM Categories
        WHERE category_id=%s
    """, (category_id,))

    category = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("edit_category.html", category=category)

@app.route("/search_suggestions")
def search_suggestions():

    query = request.args.get("q", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT product_name
        FROM Products
        WHERE product_name LIKE %s
        LIMIT 5
    """, (f"%{query}%",))

    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(products)
@app.route("/admin/users")
def admin_users():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT user_id, name, email, phone
        FROM Users
        ORDER BY user_id DESC
    """)

    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_users.html",
        users=users
    )
    
@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get all orders of this user
    cursor.execute("""
        SELECT order_id
        FROM Orders
        WHERE user_id=%s
    """, (user_id,))

    orders = cursor.fetchall()

    for order in orders:
        order_id = order["order_id"]

        cursor.execute("DELETE FROM Payments WHERE order_id=%s", (order_id,))
        cursor.execute("DELETE FROM OrderTracking WHERE order_id=%s", (order_id,))
        cursor.execute("DELETE FROM OrderItems WHERE order_id=%s", (order_id,))

    cursor.execute("DELETE FROM Orders WHERE user_id=%s", (user_id,))
    cursor.execute("DELETE FROM Reviews WHERE user_id=%s", (user_id,))
    cursor.execute("DELETE FROM Wishlist WHERE user_id=%s", (user_id,))

    # Delete cart items before cart
    cursor.execute("""
        SELECT cart_id
        FROM Cart
        WHERE user_id=%s
    """, (user_id,))

    carts = cursor.fetchall()

    for cart in carts:
        cursor.execute("DELETE FROM CartItems WHERE cart_id=%s", (cart["cart_id"],))

    cursor.execute("DELETE FROM Cart WHERE user_id=%s", (user_id,))
    cursor.execute("DELETE FROM Users WHERE user_id=%s", (user_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin/users")

@app.route("/admin/sellers")
def admin_sellers():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Sellers
        ORDER BY seller_id DESC
    """)

    sellers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_sellers.html",
        sellers=sellers
    )
@app.route("/delete_seller/<int:seller_id>")
def delete_seller(seller_id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get seller products
    cursor.execute("""
        SELECT product_id
        FROM Products
        WHERE seller_id=%s
    """, (seller_id,))

    products = cursor.fetchall()

    for product in products:
        product_id = product["product_id"]

        cursor.execute("DELETE FROM Wishlist WHERE product_id=%s", (product_id,))
        cursor.execute("DELETE FROM Reviews WHERE product_id=%s", (product_id,))
        cursor.execute("DELETE FROM CartItems WHERE product_id=%s", (product_id,))
        cursor.execute("DELETE FROM OrderItems WHERE product_id=%s", (product_id,))
        cursor.execute("DELETE FROM Inventory WHERE product_id=%s", (product_id,))
        cursor.execute("DELETE FROM Products WHERE product_id=%s", (product_id,))

    cursor.execute("DELETE FROM Sellers WHERE seller_id=%s", (seller_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin/sellers")
@app.route("/track_order/<int:order_id>")
def track_order(order_id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM OrderTracking
        WHERE order_id=%s
        ORDER BY tracking_id ASC
    """, (order_id,))

    tracking = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "track_order.html",
        tracking=tracking
    )
@app.route("/buy_now/<int:product_id>", methods=["GET", "POST"])
def buy_now(product_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            p.product_id,
            p.product_name,
            p.price,
            p.image,
            i.stock_quantity
        FROM Products p
        JOIN Inventory i
        ON p.product_id = i.product_id
        WHERE p.product_id=%s
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return redirect("/")

    if request.method == "POST":

        quantity = int(request.form["quantity"])

        if quantity < 1:
            cursor.close()
            conn.close()
            return "Invalid Quantity"

        if quantity > product["stock_quantity"]:
            cursor.close()
            conn.close()
            return "Not enough stock available"

        cursor.execute("""
            SELECT *
            FROM Cart
            WHERE user_id=%s
        """, (session["user_id"],))

        cart = cursor.fetchone()

        if not cart:

            cursor.execute("""
                INSERT INTO Cart(user_id)
                VALUES(%s)
            """, (session["user_id"],))

            conn.commit()

            cursor.execute("""
                SELECT *
                FROM Cart
                WHERE user_id=%s
            """, (session["user_id"],))

            cart = cursor.fetchone()

        cart_id = cart["cart_id"]

        cursor.execute("""
            SELECT *
            FROM CartItems
            WHERE cart_id=%s
            AND product_id=%s
        """, (cart_id, product_id))

        existing_item = cursor.fetchone()

        if existing_item:

            cursor.execute("""
                UPDATE CartItems
                SET quantity=%s
                WHERE cart_id=%s
                AND product_id=%s
            """, (
                quantity,
                cart_id,
                product_id
            ))

        else:

            cursor.execute("""
                INSERT INTO CartItems(
                    cart_id,
                    product_id,
                    quantity
                )
                VALUES(%s, %s, %s)
            """, (
                cart_id,
                product_id,
                quantity
            ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/checkout")

    cursor.close()
    conn.close()

    return render_template(
        "buy_now.html",
        product=product
    )
@app.route("/cancel_order/<int:order_id>")
def cancel_order(order_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT status
        FROM Orders
        WHERE order_id=%s
        AND user_id=%s
    """, (order_id, session["user_id"]))

    order = cursor.fetchone()

    if not order:
        cursor.close()
        conn.close()
        return redirect("/orders")

    if order["status"] not in ["Placed", "Packed"]:
        cursor.close()
        conn.close()
        return "This order cannot be cancelled now."

    cursor.execute("""
        SELECT product_id, quantity
        FROM OrderItems
        WHERE order_id=%s
    """, (order_id,))

    order_items = cursor.fetchall()

    for item in order_items:
        cursor.execute("""
            UPDATE Inventory
            SET stock_quantity = stock_quantity + %s
            WHERE product_id = %s
        """, (item["quantity"], item["product_id"]))

    cursor.execute("""
        UPDATE Orders
        SET status='Cancelled'
        WHERE order_id=%s
    """, (order_id,))

    cursor.execute("""
        INSERT INTO OrderTracking(order_id, tracking_status, tracking_date)
        VALUES(%s, %s, CURDATE())
    """, (order_id, "Cancelled"))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/orders")
@app.route("/add_quick_rating/<int:product_id>", methods=["POST"])
def add_quick_rating(product_id):

    if "user_id" not in session:
        return redirect("/login")

    rating = request.form["rating"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Reviews(
            user_id,
            product_id,
            rating,
            comment
        )
        VALUES(%s, %s, %s, %s)
    """, (
        session["user_id"],
        product_id,
        rating,
        "Quick Rating"
    ))

    cursor.execute("""
        UPDATE Products
        SET rating = (
            SELECT AVG(rating)
            FROM Reviews
            WHERE product_id=%s
        )
        WHERE product_id=%s
    """, (product_id, product_id))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/")
@app.route("/delete_order/<int:order_id>")
def delete_order(order_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM OrderTracking
        WHERE order_id=%s
    """, (order_id,))

    cursor.execute("""
        DELETE FROM Payments
        WHERE order_id=%s
    """, (order_id,))

    cursor.execute("""
        DELETE FROM OrderItems
        WHERE order_id=%s
    """, (order_id,))

    cursor.execute("""
        DELETE FROM Orders
        WHERE order_id=%s
        AND user_id=%s
    """, (
        order_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/orders")
if __name__ == "__main__":
    app.run(debug=True)