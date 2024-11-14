CREATE TABLE base_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    stat VARCHAR(1024),
    pr VARCHAR(255),
    cl VARCHAR(255),
    src VARCHAR(255),
    UNIQUE KEY unique_item (name, src)
);