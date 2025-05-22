# Custom Maintenance Responses

FastAPI Maintenance allows you to fully customize the response returned when maintenance mode is active. This is useful for providing better user experiences, custom maintenance pages, or specialized response formats.

## Default Response

By default, when maintenance mode is active, the middleware returns a JSON response with:

- Status code: `503 Service Unavailable`
- Headers: `Retry-After: 3600` (suggesting clients retry after 1 hour)
- Body: `{"detail": "Service temporarily unavailable due to maintenance"}`

## Customization

You can customize the maintenance response by providing a `response_handler` function to the middleware. This function can return any valid FastAPI/Starlette response.  Here's what you need to know:

### Function Signature

The response handler function must:
- Accept a single `Request` parameter from FastAPI
- Return a valid FastAPI/Starlette `Response` object
- Be either synchronous or asynchronous (both are supported)

```python
# Synchronous handler
def maintenance_response(request: Request) -> Response:
    # Create and return a custom response
    return JSONResponse(
        content={"status": "maintenance", "retry_after": "30 minutes"},
        status_code=503,
        headers={"Retry-After": "1800"}
    )

# Asynchronous handler
async def maintenance_response(request: Request) -> Response:
    # Create and return a custom response
    return JSONResponse(
        content={"status": "maintenance", "retry_after": "30 minutes"},
        status_code=503,
        headers={"Retry-After": "1800"}
    )
```

### Return Value

The handler can use any FastAPI/Starlette response type such as `JSONResponse`, `HTMLResponse`, `RedirectResponse`, `PlainTextResponse`, `FileResponse`, or custom responses. You can also use the request information to customize the response.

## Basic Usage

Here's a simple example that customizes the JSON response:

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

async def custom_maintenance_response(request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Maintenance in progress",
            "retry_after": "10 minutes",
            "more_info": "https://status.example.com"
        },
        headers={"Retry-After": "600"}  # 10 minutes
    )

app.add_middleware(
    MaintenanceModeMiddleware,
    response_handler=custom_maintenance_response
)
```

## Examples

### HTML Maintenance Page

You can return an HTML maintenance page instead of JSON:

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

async def html_maintenance_page(request: Request) -> HTMLResponse:
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Site Maintenance</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 30px;
                    text-align: center;
                    color: #333;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }
                h1 {
                    color: #e74c3c;
                }
                .status-time {
                    font-style: italic;
                    color: #7f8c8d;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Site Under Maintenance</h1>
                <p>We're currently performing scheduled maintenance to improve our services.</p>
                <p>Please check back soon. We apologize for any inconvenience.</p>
                <p class="status-time">Expected completion: 2 hours</p>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(
        content=html_content,
        status_code=503,
        headers={"Retry-After": "7200"}  # 2 hours
    )

app.add_middleware(
    MaintenanceModeMiddleware,
    response_handler=html_maintenance_page
)
```

### Content Negotiation

You can implement content negotiation to return different formats based on the request's `Accept` header:

```python
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

async def content_negotiated_response(request: Request) -> Response:
    accept = request.headers.get("accept", "")

    # Return HTML for browser requests
    if "text/html" in accept:
        html_content = "<html><body><h1>Under Maintenance</h1><p>Please check back later.</p></body></html>"
        return HTMLResponse(content=html_content, status_code=503)

    # Return plain text for text requests
    if "text/plain" in accept:
        return PlainTextResponse(content="Service under maintenance. Please check back later.", status_code=503)

    # Default to JSON
    return JSONResponse(
        content={"status": "maintenance", "message": "Service temporarily unavailable"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE
    )

app.add_middleware(
    MaintenanceModeMiddleware,
    response_handler=content_negotiated_response
)
```

### Using Templates

You can integrate with FastAPI's template system for more sophisticated HTML responses:

```python
from fastapi import FastAPI, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

# Set up templates
templates = Jinja2Templates(directory="templates")

async def template_maintenance_page(request: Request) -> Response:
    # Pass data to the template
    return templates.TemplateResponse(
        "maintenance.html",
        {"request": request, "site_name": "My API", "estimated_time": "2 hours"},
        status_code=503
    )

app.add_middleware(
    MaintenanceModeMiddleware,
    response_handler=template_maintenance_page
)
```

With a template file at `templates/maintenance.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ site_name }} - Maintenance</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Your CSS styles here */
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ site_name }} is under maintenance</h1>
        <p>We're working on improving our services. Please check back soon.</p>
        <p>Estimated completion time: {{ estimated_time }}</p>
    </div>
</body>
</html>
```

### Using Request Information

The handler function receives the request object, so you can customize responses based on the request parameters:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi_maintenance import MaintenanceModeMiddleware

app = FastAPI()

async def path_aware_response(request: Request) -> JSONResponse:
    # Customize message based on path
    path = request.url.path

    if path.startswith("/api/v1"):
        message = "API v1 is undergoing maintenance. Please use API v2."
    elif path.startswith("/api/v2"):
        message = "API v2 is being updated. Please try again later."
    else:
        message = "Service temporarily unavailable due to maintenance."

    return JSONResponse(
        content={"detail": message, "path": path},
        status_code=503
    )

app.add_middleware(
    MaintenanceModeMiddleware,
    response_handler=path_aware_response
)
```
