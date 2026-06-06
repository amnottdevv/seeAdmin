#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
seeAdmin - Advanced Admin & Login Page Scanner
Author: seeAdmin Tools
Description: Multi-stage scanner for admin panels, folders, and files.
"""

import argparse
import requests
import threading
from urllib.parse import urljoin
from queue import Queue
from typing import List, Dict, Set
import sys
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.tree import Tree
import pyfiglet

console = Console()

# Konfigurasi default
DEFAULT_TIMEOUT = 5
DEFAULT_THREADS = 10
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
]

class RobustScanner:
    def __init__(self, target: str, threads: int = DEFAULT_THREADS, timeout: int = DEFAULT_TIMEOUT, output: str = None):
        self.target = target.rstrip('/')
        self.threads = threads
        self.timeout = timeout
        self.output = output
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENTS[0]})
        
        # Hasil scan
        self.wordlist_results: List[Dict] = []
        self.folder_results: List[Dict] = []  # hasil dari path.txt (folder)
        self.file_results: List[Dict] = []    # hasil scan file di dalam folder yang ditemukan
        
        self.lock = threading.Lock()
    
    def load_file(self, filename: str) -> List[str]:
        """Memuat daftar dari file, return list of stripped lines."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            return lines
        except FileNotFoundError:
            console.print(f"[red]Error: File '{filename}' tidak ditemukan![/red]")
            return []
    
    def check_path(self, path: str) -> Dict:
        """Mengecek satu path pada target."""
        url = urljoin(self.target + '/', path)
        result = {
            'url': url,
            'status': 0,
            'title': '',
            'is_login': False
        }
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=False)
            result['status'] = resp.status_code
            
            if resp.status_code == 200:
                content = resp.text.lower()
                login_keywords = ['username', 'user', 'email', 'password', 'login', 'signin']
                result['is_login'] = any(kw in content for kw in login_keywords)
                # Ambil title
                if '<title>' in content:
                    start = content.find('<title>') + 7
                    end = content.find('</title>', start)
                    result['title'] = content[start:end].strip()[:60]
                else:
                    result['title'] = 'No title'
            elif resp.status_code in [301, 302, 307, 308]:
                result['title'] = f"Redirect → {resp.headers.get('Location', '?')}"
            else:
                result['title'] = '-'
        except requests.exceptions.Timeout:
            result['status'] = 408
            result['title'] = 'Timeout'
        except requests.exceptions.ConnectionError:
            result['status'] = 0
            result['title'] = 'Connection Error'
        except Exception:
            result['status'] = 0
            result['title'] = 'Error'
        return result
    
    def scan_paths(self, paths: List[str], results_list: List[Dict], description: str) -> None:
        """Multi-thread scanning untuk daftar path."""
        if not paths:
            return
        queue = Queue()
        for p in paths:
            queue.put(p)
        
        with Progress(
            TextColumn(f"[progress.description]{description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("", total=len(paths))
            
            def worker():
                while not queue.empty():
                    path = queue.get()
                    result = self.check_path(path)
                    with self.lock:
                        results_list.append(result)
                    progress.update(task, advance=1)
                    queue.task_done()
            
            threads = []
            for _ in range(min(self.threads, len(paths))):
                t = threading.Thread(target=worker)
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
            queue.join()
    
    def scan_wordlist(self, wordlist_file: str = "wordlists.txt"):
        """Stage 1: Scan dengan wordlists.txt (path umum admin/login)"""
        paths = self.load_file(wordlist_file)
        if not paths:
            return
        console.print(f"\n[bold cyan]▶ Stage 1: Scanning general admin/login paths[/bold cyan] (from {wordlist_file})")
        self.scan_paths(paths, self.wordlist_results, "[yellow]Wordlist scan")
    
    def scan_folders(self, folder_file: str = "path.txt"):
        """Stage 2: Scan folder admin dari path.txt, simpan hasil di self.folder_results"""
        folders = self.load_file(folder_file)
        if not folders:
            return
        console.print(f"\n[bold cyan]▶ Stage 2: Scanning admin folders[/bold cyan] (from {folder_file})")
        self.scan_paths(folders, self.folder_results, "[green]Folder scan")
    
    def scan_files_in_folders(self, file_list_file: str = "file.txt"):
        """Stage 3: Untuk setiap folder yang ditemukan (status 200), scan file dari file.txt di dalam folder tersebut"""
        files = self.load_file(file_list_file)
        if not files:
            return
        
        # Ambil folder yang sukses (status 200) dari hasil folder scan
        found_folders = [r for r in self.folder_results if r['status'] == 200]
        if not found_folders:
            console.print("[yellow]Tidak ada folder ditemukan, skip file scan.[/yellow]")
            return
        
        console.print(f"\n[bold cyan]▶ Stage 3: Scanning files inside discovered folders[/bold cyan] (from {file_list_file})")
        all_paths = []
        for folder in found_folders:
            # Ambil path relatif folder dari URL
            folder_url = folder['url']
            # Ekstrak path setelah target
            relative = folder_url[len(self.target):].lstrip('/')
            for f in files:
                # gabungkan folder + file
                full_path = f"{relative}/{f}" if relative else f
                all_paths.append(full_path)
        
        # Hapus duplikat
        all_paths = list(set(all_paths))
        if all_paths:
            self.scan_paths(all_paths, self.file_results, "[magenta]File scan inside folders")
    
    def display_results(self):
        """Tampilkan hasil dengan tabel dan tree yang rapi"""
        console.print("\n")
        
        # Tabel untuk Stage 1 (wordlist)
        if self.wordlist_results:
            important1 = [r for r in self.wordlist_results if r['status'] in [200, 301, 302, 401, 403]]
            if important1:
                table1 = Table(title="[bold]Stage 1: General Paths[/bold]", show_header=True, header_style="bold cyan")
                table1.add_column("Status", width=8)
                table1.add_column("URL", no_wrap=False)
                table1.add_column("Info")
                for res in important1[:20]:  # batasi tampilan
                    status_str = f"[green]{res['status']}[/green]" if res['status'] == 200 else f"[yellow]{res['status']}[/yellow]" if res['status'] in [301,302] else f"[red]{res['status']}[/red]"
                    info = "🔐 LOGIN" if res.get('is_login') else res['title']
                    table1.add_row(status_str, res['url'], info)
                console.print(table1)
        
        # Tabel untuk Stage 2 (folders)
        if self.folder_results:
            folders_found = [r for r in self.folder_results if r['status'] == 200]
            if folders_found:
                table2 = Table(title="[bold]Stage 2: Discovered Admin Folders[/bold]", show_header=True, header_style="bold green")
                table2.add_column("No", width=4)
                table2.add_column("Folder URL")
                table2.add_column("Info")
                for idx, res in enumerate(folders_found, 1):
                    info = "🔐 LOGIN" if res.get('is_login') else res['title']
                    table2.add_row(str(idx), res['url'], info)
                console.print(table2)
        
        # Tree untuk Stage 3 (files inside folders)
        if self.file_results:
            files_found = [r for r in self.file_results if r['status'] == 200]
            if files_found:
                console.print("[bold magenta]Stage 3: Files Found Inside Folders[/bold magenta]")
                tree = Tree("📁 Discovered Files")
                # Kelompokkan berdasarkan folder induk
                folder_map = {}
                for res in files_found:
                    url = res['url']
                    # cari folder induk
                    for folder in [r for r in self.folder_results if r['status'] == 200]:
                        if url.startswith(folder['url']):
                            parent = folder['url']
                            if parent not in folder_map:
                                folder_map[parent] = []
                            folder_map[parent].append(res)
                            break
                for parent, children in folder_map.items():
                    branch = tree.add(f"[cyan]{parent}[/cyan]")
                    for child in children:
                        branch.add(f"[green]{child['url']}[/green] - {child['title'][:50]}")
                console.print(tree)
        
        # Ringkasan total
        total_found = len([r for r in self.wordlist_results if r['status']==200]) + \
                      len([r for r in self.folder_results if r['status']==200]) + \
                      len([r for r in self.file_results if r['status']==200])
        console.print(Panel(f"[bold]Total ditemukan:[/bold] {total_found} halaman/folder/file", title="Summary", border_style="blue"))
    
    def save_results(self):
        """Simpan semua hasil ke file jika opsi output diberikan"""
        if self.output:
            try:
                with open(self.output, 'w', encoding='utf-8') as f:
                    f.write(f"# seeAdmin Scan Results\nTarget: {self.target}\n\n")
                    f.write("## STAGE 1: WORDLIST PATHS\n")
                    for res in self.wordlist_results:
                        if res['status'] in [200,301,302,403]:
                            f.write(f"{res['status']} -> {res['url']} | {res['title']}\n")
                    f.write("\n## STAGE 2: ADMIN FOLDERS\n")
                    for res in self.folder_results:
                        if res['status'] == 200:
                            f.write(f"{res['status']} -> {res['url']} | {res['title']}\n")
                    f.write("\n## STAGE 3: FILES INSIDE FOLDERS\n")
                    for res in self.file_results:
                        if res['status'] == 200:
                            f.write(f"{res['status']} -> {res['url']} | {res['title']}\n")
                console.print(f"[green]Hasil disimpan ke {self.output}[/green]")
            except Exception as e:
                console.print(f"[red]Gagal menyimpan: {e}[/red]")

def main():
    banner = pyfiglet.figlet_format("seeAdmin", font="slant")
    console.print(f"[bold cyan]{banner}[/bold cyan]")
    console.print("[italic]Advanced Admin Panel & File Scanner[/italic]\n", style="dim")
    
    # Mode interaktif jika tidak ada argumen
    if len(sys.argv) == 1:
        target = console.input("[bold yellow]Masukkan target URL (http://example.com): [/bold yellow]").strip()
        if not target.startswith(('http://','https://')):
            console.print("[red]URL harus diawali http:// atau https://[/red]")
            return
        threads = DEFAULT_THREADS
        timeout = DEFAULT_TIMEOUT
        output = None
    else:
        parser = argparse.ArgumentParser(description="Advanced Admin Scanner")
        parser.add_argument("-u", "--url", required=True, help="Target URL")
        parser.add_argument("-t", "--threads", type=int, default=DEFAULT_THREADS)
        parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
        parser.add_argument("-o", "--output", help="Simpan hasil ke file")
        args = parser.parse_args()
        target = args.url
        threads = args.threads
        timeout = args.timeout
        output = args.output
    
    scanner = RobustScanner(target, threads, timeout, output)
    console.print(f"[bold]Target:[/bold] {target}\n")
    
    # Jalankan 3 stage
    scanner.scan_wordlist("wordlists.txt")
    scanner.scan_folders("path.txt")
    scanner.scan_files_in_folders("file.txt")
    
    scanner.display_results()
    scanner.save_results()

if __name__ == "__main__":
    main()