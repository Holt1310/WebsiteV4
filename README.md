# TruckSoft Website

This repository contains a small Flask application that serves TruckSoft guides and documentation via a modern Bootstrap interface. The landing page lists resources defined in `resources.json` rather than scanning the folder. Logged in admins can add new resources from the **Resources** page by providing a title, description, and either uploading a file or entering a URL. Resources may include a `<DYNAMIC>` placeholder that visitors replace when opening the link.

The **How To** section is implemented as a simple forum. Browse the posts or login with a password to publish new instructions using a lightweight rich text editor built directly into the page. Posts may include uploaded attachments or images. Logged in admins can edit, delete, or lock posts to prevent further changes. This editor includes buttons for formatting, lists, links, image uploads, line spacers, grids, and code blocks without relying on TinyMCE. Images can be dragged to new positions, pasted from the clipboard, and the editor area grows as you type. Images embedded in the post are not repeated in the attachment list. Posts are organized into categories shown in a sidebar tab layout. Admins manage categories from the **Categories** page and choose one whenever posting or editing. Categories can also be renamed or removed from that page. Posts can also include **tags** provided as comma separated text. The forum page lists all existing tags with checkboxes so you can filter posts by category, tag, and search text for granular results.
Long posts are truncated in the forum view. Click **Open** on any post to read the full text and add comments.

## Setup

Create a Python virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the site

Run the application with:

```bash
python app.py
```

Open `http://localhost:5000` in your browser (or the host/port you configure).
Use the **Login** link to enter the admin password and create new posts. The
default password can be set with the `TRUCKSOFT_ADMIN_PASSWORD` environment
variable. The host and port may be customized with `TRUCKSOFT_HOST` and
`TRUCKSOFT_PORT`.


