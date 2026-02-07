
# Classic Cocktails & Signatures API 🍸

A robust Django REST Framework backend serving a curated collection of classic and signature cocktail recipes. This repository contains **only the backend API code**.

## 🚀 Features

- **Browsable API**: Fully explorable API root via Django REST Framework at `/api/`.
- **Full CRUD Operations**: Create, Read, Update, and Delete cocktails and ingredients via standard REST methods.
- **Authoring Endpoints**: Publicly accessible endpoints for adding new recipes and managing metadata (categories, tags, etc.).
- **Recipe Management**: Standardized models for Drinks, Ingredients (Recipe & Garnish), Glass Types, and Preparation Methods.
- **Search & Filter**: Powerful filtering by name, category, and ingredients.
- **Image Handling**: Optimized image serving with `Pillow`.

> **Note**: This repository does not include the actual image files. You will need to populate the `media/drinks/` directory with your own images or update the database to point to hosted URLs.

## 🛠️ Tech Stack

- **Python**: 3.12+
- **Django**: 5.0+
- **Django REST Framework**: 3.15+
- **Pillow**: Image processing

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/classic-cocktails-api.git
    cd classic-cocktails-api
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Apply migrations**:
    ```bash
    python manage.py migrate
    ```

5.  **Run the server**:
    ```bash
    python manage.py runserver
    ```

   Open [http://127.0.0.1:8000/api/](http://127.0.0.1:8000/api/) to explore the API.
   
   > **Note**: As this is a backend-only repository, the root URL `/` will likely return a 404. Please navigate to `/api/` to interact with the application.

## 🔑 Configuration

Create a `.env` file in the root directory if you wish to override default settings (though defaults work out-of-the-box for development):

```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
```

## 🍹 API Endpoints

### Primary Endpoints
- `/api/All_Cocktails/`: List (GET) and Create (POST) cocktails.
- `/api/All_Cocktails/<slug>/`: Retrieve, Update (PUT/PATCH), and Delete (DELETE) a specific cocktail.
- `/api/All_Cocktails/random/`: Get a random cocktail.

### Metadata Endpoints
- `/api/categories/`: Manage drink categories.
- `/api/ingredients/`: Manage recipe ingredients.
- `/api/garnish_ingredients/`: Manage garnish options.
- `/api/tags/`: Manage tags.
- `/api/glass_types/`: Manage glass types.
- `/api/preparation_methods/`: Manage preparation methods.

> **Note**: The Django Admin interface has been intentionally disabled for this public export to focus on the REST API capabilities.

## 📄 License

[MIT](LICENSE)
