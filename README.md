# URL Shortener and Analytics Service

Welcome to the **Microsh URL Shortener** project! This is a URL shortening service with integrated analytics and user management. It allows users to shorten long URLs, track clicks on the shortened links, and view analytics like unique clicks, geographic data, and more.

---

## Features:

- **URL Shortening**: Shorten long URLs and create custom short URLs.
- **Link Analytics**: Track clicks on shortened URLs, including unique clicks, timestamp-based analytics (minute, hour, day, week, month), and click data by country.
- **User Authentication**: OAuth2-based authentication system for user management.
- **User Profile Management**: Retrieve and manage user data from external APIs (e.g., ShareTribe).
- **Click Tracking**: Store and retrieve detailed information about each click, including user agent, IP address, and timestamp.
- **Data Retrieval**: Retrieve detailed link and click statistics, including unique clicks and geographical data.

---

## Technologies Used:

- **FastAPI**: A modern, fast web framework for building APIs with Python 3.7+.
- **SQLAlchemy**: Object-Relational Mapping (ORM) for interacting with databases.
- **JWT**: JSON Web Tokens for secure user authentication.
- **PostgreSQL**: Relational database used for storing user and link data.
- **Docker**: Containerization of the application for easy deployment.
- **Pydantic**: Data validation and settings management using Python data types.

---

## Endpoints:

### 1. **Authentication**

- **POST /v1/auth/token**  
  Authenticates a user via username and password and returns a JWT access token.

- **GET /api/users/me**  
  Returns the details of the currently authenticated user.

### 2. **Shorten URL**

- **POST /api/shorten**  
  Shortens a given URL and returns the shortened link. Users can also create custom short URLs.

- **GET /{short_url}**  
  Redirects to the long URL from the short URL provided.

### 3. **Link Management**

- **GET /api/bitlinks**  
  Returns a list of links created by the currently authenticated user.

- **GET /api/bitlinks/active**  
  Returns a list of active (non-expired) links created by the authenticated user.

- **GET /api/bitlinks/{link_id}**  
  Returns details of a specific link by its ID.

- **DELETE /api/bitlinks/{link_id}**  
  Deletes a specific link by marking it as expired.

### 4. **Click Analytics**

- **GET /api/bitlinks/{link_id}/clicks/unique**  
  Returns unique clicks on a given shortened link, based on a combination of IP and user agent.

- **GET /api/bitlinks/{link_id}/clicks**  
  Returns detailed click analytics for a given shortened link, based on the selected time unit (minute, hour, day, week, month).

- **GET /api/bitlinks/{link_id}/countries**  
  Returns click data for a given shortened link, broken down by country.

---

## Running the Application

### Prerequisites:

- **Python 3.7+**
- **PostgreSQL Database**
- **Docker (for containerized deployment)**

### Local Development:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/microsh-url-shortener.git
   cd microsh-url-shortener
