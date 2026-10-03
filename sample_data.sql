USE online_shopping_dbms;

-- CATEGORIES
INSERT INTO Categories(category_name)
VALUES
('Mobiles'),
('Fashion'),
('Electronics'),
('Home Appliances');

-- SELLERS
INSERT INTO Sellers(seller_name,email,phone)
VALUES
('Tech World','tech@gmail.com','9876543210'),
('Fashion Hub','fashion@gmail.com','9876500000');

-- PRODUCTS
INSERT INTO Products
(product_name,description,price,category_id,seller_id)
VALUES
(
'iQOO Neo 10',
'Gaming smartphone with AMOLED display',
29999,
1,
1
),
(
'Bluetooth Headphones',
'Wireless high bass headphones',
1999,
3,
1
),
(
'Men Casual Shirt',
'Stylish cotton casual shirt',
799,
2,
2
);

-- INVENTORY
INSERT INTO Inventory(product_id,stock_quantity)
VALUES
(1,50),
(2,100),
(3,200);