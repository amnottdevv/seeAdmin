
# seeAdmin – Admin & Login Page Scanner

A smart, multi‑stage scanner that hunts for admin panels, login pages, hidden folders, and juicy files inside discovered directories.  
Comes with a colorful terminal UI, progress bars, and a clean result table.

## Features

- **3‑stage scanning**  
  1. General admin/login paths (from `wordlists.txt`)  
  2. Admin folders (from `path.txt`)  
  3. Files inside found folders (from `file.txt`)  

- **Smart detection** – automatically marks login pages.  
- **Multi‑threaded** – fast scanning.  
- **Interactive mode** – just run `python main.py` and enter the target URL.  
- **Command line mode** – full control with flags.  
- **Beautiful output** – tables, trees, colours, and progress bars (thanks to `rich`).

## Requirements

- Python 3.6+  
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Files you need

| File          | What it contains                               |
|---------------|------------------------------------------------|
| `wordlists.txt` | common admin/login paths (admin, login, wp‑admin, etc.) |
| `path.txt`      | admin folder names (admin, administrator, panel, ...) |
| `file.txt`      | file names/extensions to look for inside folders (`index.php`, `config.js`, etc.) |

You can edit or replace these with your own wordlists.

## Usage

### Interactive mode (no arguments)
```bash
python main.py
```
Just type the target URL when asked.

### Command line mode
```bash
python main.py -u http://example.com -t 15 -o results.txt
```

### Options

| Flag           | Description                                    |
|----------------|------------------------------------------------|
| `-u, --url`    | Target URL (required in CLI mode)              |
| `-t, --threads`| Number of threads (default: 10)                |
| `--timeout`    | Request timeout in seconds (default: 5)        |
| `-o, --output` | Save results to a file                         |

## Example

```bash
python main.py -u https://testsite.com -t 20 --timeout 3 -o found.txt
```

Output will show:
- Stage 1 results (general paths)
- Stage 2 results (folders found)
- Stage 3 results (files inside those folders, shown as a tree)

All findings are also saved to `found.txt` if you use `-o`.

## How it works

1. **Stage 1** – scans `wordlists.txt` against the target.  
2. **Stage 2** – scans `path.txt` to find admin folders (status 200).  
3. **Stage 3** – takes every folder found in Stage 2, then scans for files from `file.txt` inside those folders.  

This way you don't blindly scan millions of paths – you first find the folders, then dig deeper.

## Note

Use only on systems you own or have permission to test. Don't be a jerk.

## License

Do whatever you want with it. Just don't blame me if something breaks.
