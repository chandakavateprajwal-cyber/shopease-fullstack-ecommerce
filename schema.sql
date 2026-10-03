DROP DATABASE IF EXISTS online_shopping_dbms;

CREATE DATABASE online_shopping_dbms;

USE online_shopping_dbms;

-- USERS TABLE
CREATE TABLE Users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    phone VARCHAR(15),
    address TEXT
);

-- SELLERS TABLE
CREATE TABLE Sellers (
    seller_id INT PRIMARY KEY AUTO_INCREMENT,
    seller_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(15),
    password VARCHAR(255)
);

-- CATEGORIES TABLE
CREATE TABLE Categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100),
    image TEXT
);

-- PRODUCTS TABLE
CREATE TABLE Products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(100),
    description TEXT,
    price DECIMAL(10,2),
    image TEXT,
    discount INT DEFAULT 0,
    rating DECIMAL(3,1) DEFAULT 4.0,
    category_id INT,
    seller_id INT,

    FOREIGN KEY (category_id)
    REFERENCES Categories(category_id),

    FOREIGN KEY (seller_id)
    REFERENCES Sellers(seller_id)
);

-- INVENTORY TABLE
CREATE TABLE Inventory (
    inventory_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    stock_quantity INT,

    FOREIGN KEY (product_id)
    REFERENCES Products(product_id)
);

-- CART TABLE
CREATE TABLE Cart (
    cart_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,

    FOREIGN KEY (user_id)
    REFERENCES Users(user_id)
);

-- CART ITEMS TABLE
CREATE TABLE CartItems (
    cart_item_id INT PRIMARY KEY AUTO_INCREMENT,
    cart_id INT,
    product_id INT,
    quantity INT,

    FOREIGN KEY (cart_id)
    REFERENCES Cart(cart_id),

    FOREIGN KEY (product_id)
    REFERENCES Products(product_id)
);

-- WISHLIST TABLE
CREATE TABLE Wishlist (
    wishlist_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    product_id INT,

    FOREIGN KEY (user_id)
    REFERENCES Users(user_id),

    FOREIGN KEY (product_id)
    REFERENCES Products(product_id),

    UNIQUE(user_id, product_id)
);

-- ORDERS TABLE
CREATE TABLE Orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    order_date DATE,
    total_amount DECIMAL(10,2),
    status VARCHAR(50),

    FOREIGN KEY (user_id)
    REFERENCES Users(user_id)
);

-- ORDER ITEMS TABLE
CREATE TABLE OrderItems (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    product_id INT,
    quantity INT,
    price DECIMAL(10,2),

    FOREIGN KEY (order_id)
    REFERENCES Orders(order_id),

    FOREIGN KEY (product_id)
    REFERENCES Products(product_id)
);

-- PAYMENTS TABLE
CREATE TABLE Payments (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    payment_method VARCHAR(50),
    payment_status VARCHAR(50),
    payment_date DATE,

    FOREIGN KEY (order_id)
    REFERENCES Orders(order_id)
);

-- REVIEWS TABLE
CREATE TABLE Reviews (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    product_id INT,
    rating INT,
    comment TEXT,

    FOREIGN KEY (user_id)
    REFERENCES Users(user_id),

    FOREIGN KEY (product_id)
    REFERENCES Products(product_id)
);

-- ORDER TRACKING TABLE
CREATE TABLE OrderTracking (
    tracking_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    tracking_status VARCHAR(100),
    trackingrder_date DATE,

    FOREIGN KEY (order_id)
    REFERENCES Orders(order_id)
);
