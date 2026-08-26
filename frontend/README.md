# CSV Insight frontend

Frontend MVP built with plain HTML, CSS, and JavaScript.

## Run locally

Open `index.html` directly in a browser or run a static server:

```bash
python -m http.server 5500 --directory frontend
```

Then visit `http://localhost:5500`.

## Future Flask integration

CSV files are currently read in the browser so the interface can work independently. When the backend is ready, replace the `FileReader` logic in `handleFile()` with a `fetch()` request that sends `FormData` to a Flask endpoint such as `POST /api/upload`.
