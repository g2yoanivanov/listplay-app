# ListPlay 🎵

A robust Django **REST** Framework (**DRF**) **API** that seamlessly integrates with the Spotify Web **API**. ListPlay allows users to authenticate securely via Spotify, search the global Spotify catalog, curate local playlists, and export those playlists directly to their native Spotify accounts.

## ✨ Key Features & Business Logic

* **Spotify OAuth 2.0 Integration:** Secure authorization code flow that handles Access and Refresh tokens. Tokens are securely exchanged server-to-server, ensuring sensitive data (like the Client Secret or Refresh Token) is never exposed in the browser or **URL** parameters.

* **Catalog Search:** Real-time track searching querying the Spotify Web **API**, parsing complex nested data (like multiple artists) into a clean, frontend-ready format.

* **Smart Local Storage & Data Integrity:** Bridges external Spotify data with the local database using intelligent get_or_create logic. Handles complex ManyToMany relationships between Track and Artist models dynamically. Prevents database bloat by ensuring no duplicate tracks or artists are ever created, even if added by multiple users.

* **Idempotent API Design:**
Graceful handling of duplicate requests. If a user attempts to add a track that already exists in their playlist, the **API** safely returns a **200** OK instead of an error, ensuring a smooth frontend user experience and preventing *double-click* conflicts.

* **Direct Spotify Export:**
Push locally curated playlists directly to a user's Spotify profile in a single click, utilizing bulk **URI** additions to optimize **API** requests.

## 🛠️ Tech Stack

* **Backend Framework:** Python, Django, Django REST Framework (**DRF**)

* **Infrastructure & Deployment:** Docker, Docker Compose

* **Third-Party Integrations:** Spotify Web API

* **Database:** PostgreSQL (Containerized)

* **Authentication:** OAuth 2.0, DRF Token Authentication

## 🚀 Installation & Setup (Docker)

* **Clone the repository:**

```bash
git clone https://github.com/g2yoanivanov/listplay-app.git```
cd listplay 
```

* **Configure Environment Variables:**

Create a .env file in the root directory. Docker will automatically read this to configure the Django backend and PostgreSQL database:

* **Django Settings**

```
DJANGO_SECRET_KEY=your_django_secret_key
DEBUG=True 
```

* **Database Settings**

```
POSTGRES_DB=listplay_db POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db POSTGRES_PORT=5432
```

* **Spotify API Credentials**

```
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/api/spotify/callback/
```

* **Build and Start the Containers**

```bash
docker-compose up --build
```

The **API** will be available at [http://localhost:**8000**.](http://localhost:8000.)

* **Apply Database Migrations**

Open a new terminal window and run:

```bash
docker-compose run --rm app sh -c "python manage.py migrate"
```

* **Create a Superuser (Optional for Admin Access)**

```bash
docker-compose run --rm app sh -c "python manage.py createsuperuser"
```

## 📡 API Endpoints & Routing

The API is fully documented using **drf-spectacular** and provides a Swagger UI for easy testing and exploration. All main application endpoints are prefixed with `/api/`.

### 📖 Documentation & Admin
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/admin/` | Django Admin panel for database management. |
| `GET` | `/api/schema/` | OpenAPI 3.0 schema download. |
| `GET` | `/api/docs/` | **Swagger UI** - Interactive API documentation and testing interface. |

### 👤 User Management (`/api/user/`)
*Handles user registration, authentication, and profile management.*
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/user/create/` | Register a new user account. |
| `POST` | `/api/user/token/` | Obtain an auth token (Login). |
| `GET/PUT` | `/api/user/me/` | Retrieve or update the authenticated user's profile. |

### 🎵 Playlist & Track Management (`/api/playlist/`)
*Handles local CRUD operations for playlists and intermediate track logic.*
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET/POST` | `/api/playlist/` | List all playlists for the user or create a new one. |
| `GET/PUT/DEL`| `/api/playlist/<id>/` | Retrieve, update, or delete a specific playlist. |
| `POST` | `/api/playlist/<id>/add-track/`| Save a Spotify track/artists to the local DB and link to the playlist. |

### 🟢 Spotify Integration (`/api/spotify/`)
*Handles OAuth 2.0 flow and external Spotify API communication.*
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/spotify/auth-url/` | Generate the Spotify OAuth login URL. |
| `GET` | `/api/spotify/callback/` | Handle the Spotify redirect and save OAuth tokens. |
| `GET` | `/api/spotify/search/?q=<query>` | Search the external Spotify catalog. |
| `POST` | `/api/spotify/export/<id>/` | Export a local playlist to the user's actual Spotify account. |

> **Authentication Note:** Endpoints interacting with user data or Spotify features require an authorization header: `Authorization: Token <user_token>`.

## 🗄️ Database Models (Schema) 
* **User (Custom):**
Replaces the default Django user model. Uses a secure **UUID** primary key and enforces email-based authentication instead of usernames.

* **SpotifyToken:** A One-to-One mapping to the User. Securely stores OAuth credentials (access_token, refresh_token) and includes built-in utility methods (is_valid(), refresh()) to autonomously manage session expiration and token renewals.

* **Playlist:** The core container for curated music. Features a **UUID** primary key, privacy controls (is_public), custom cover image uploads, and relates directly to the User who created it.

* **Track:**  A local cache of a Spotify song. Stores the essential metadata (spotify_id, title, duration_ms, cover_url) and connects to Artist via a ManyToMany relationship.

* **Artist & Genre:** Represents musicians and their associated music categories. Artists are stored via their spotify_id and maintain a ManyToMany relationship with both Track and Genre.

* **PlaylistTrack (Through Model):** A custom intermediate table managing the ManyToMany relationship between Playlist and Track. It explicitly handles the order of songs within a playlist and utilizes strict unique_together constraints to prevent duplicate track placements or ordering conflicts.

## 🧪 Running Tests

The project includes an automated test suite to ensure data integrity and reliable API behavior. Since the application heavily relies on the Spotify Web API, external HTTP requests are mocked using Python's `unittest.mock`. This ensures the test suite is fast, reliable, and runs in total isolation without requiring active Spotify tokens or a live internet connection.

**Run the entire test suite:**
```bash
docker-compose run --rm app sh -c "python manage.py test"
```

## 📄 License

Distributed under the MIT License. See `MIT license` for more information.

## 📫 Contact

**Yoan Ivanov**
* **GitHub:** [@g2yoanivanov](https://github.com/g2yoanivanov)
* **LinkedIn:** [linkedin.com/in/yoan-ivanov](https://www.linkedin.com/in/yoan-ivanov-17473836b/)

**Project Link:** [https://github.com/g2yoanivanov/listplay-app](https://github.com/g2yoanivanov/listplay-app)
