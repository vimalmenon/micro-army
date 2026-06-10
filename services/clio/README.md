# Clio — DynamoDB Service

**Muse of History**

In Greek mythology, Clio (Κλειώ) is the Muse of History — keeper of records, chronicler of all that has come before. She is often depicted with a scroll or a chest of books.

**Why Clio?**

This microservice is the single source of truth for all data in the micro-army ecosystem. It owns the `vimal` DynamoDB table using the `CA#` partition convention for single-table design. Like Clio preserving history, this service stores and retrieves every record.

**Domain:** Data persistence & retrieval
**Dependencies:** AWS DynamoDB
**Consumed by:** All other microservices
