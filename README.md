# BridgeLabs

A responsive curriculum-to-career workspace built with HTML, CSS, and vanilla JavaScript.

## Run locally

Open `index.html` in a browser, or run `python3 -m http.server 5173` in this folder and visit http://localhost:5173.

## Included

- Responsive dashboard and original visual identity
- Accessible PDF picker and drag-and-drop zone
- PDF extension/MIME checks, empty-file checks, and a 10 MB limit
- Selected-file details, replacement and removal
- Clearly labeled sample analysis flow
- Curriculum session view and product information dialog

Files remain in browser memory and are cleared on refresh. Nothing is uploaded to a server. PDF text extraction, live job data, real skill-gap scoring, accounts, and GitHub integration are not implemented. The analysis cards are examples only. A production service should validate PDF content on the server as well.

Fonts load from Google Fonts with local sans-serif fallbacks. No build process or dependencies are required.
