import http.server
import socketserver
import webbrowser
import os
import threading

PORT = 8000

def scan_html_files():
    """Scans the current working directory for HTML files."""
    current_dir = os.getcwd()
    html_files = [f for f in os.listdir(current_dir) if f.endswith('.html')]
    return sorted(html_files)

def main():
    while True: # Master loop for back-and-forth navigation
        html_files = scan_html_files()
        
        print("\n" + "=" * 60)
        print(" 🌐 INCEPTION QUIZ SERVER - INTERACTIVE HTML LAUNCHER 🌐")
        print("=" * 60)
        
        if not html_files:
            print("❌ [WARNING]: No HTML files found in the current directory!")
        else:
            print("Please select an HTML file to launch:\n")
            for idx, file in enumerate(html_files, start=1):
                print(f"  [{idx}] 📄 {file}")
        
        print("-" * 60)
        print("  [R] 🔄 Refresh / Rescan Directory")
        print("  [0] ❌ Exit / Quit")
        print("=" * 60)

        # Selection loop with validation
        selected_file = None
        while True:
            choice = input("👉 Enter your choice: ").strip().lower()
            
            if choice == '0':
                print("👋 Exiting server launcher. Have a great day!")
                return
            
            if choice == 'r':
                print("🔄 Rescanning directory...")
                break # Breaks inner loop to restart the outer loop (rescan)
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(html_files):
                    selected_file = html_files[idx]
                    break
                    
            print("❌ Invalid selection. Choose a valid number, type 'r' to refresh, or '0' to exit.")

        # If user chose to refresh, restart the loop
        if choice == 'r':
            continue

        if selected_file:
            Handler = http.server.SimpleHTTPRequestHandler
            url = f"http://localhost:{PORT}/{selected_file}"

            print("\n" + "=" * 60)
            print(f"🚀 Starting Inception Quiz Server...")
            print(f"🌐 Target URL: {url}")
            print(f"🛑 Press [Enter] in this terminal anytime to stop the server & go back.")
            print("=" * 60 + "\n")
            
            # Start the server in a background thread
            httpd = socketserver.TCPServer(("", PORT), Handler)
            server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()

            # Automatically open browser to the chosen file
            webbrowser.open(url)

            # Wait for user input to stop the server and go back to menu
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass

            print("\n🛑 Shutting down server gracefully...")
            try:
                httpd.shutdown()
                httpd.server_close()
            except Exception:
                pass
            print("✅ Server stopped. Returning to file selection menu...\n")

if __name__ == "__main__":
    main()