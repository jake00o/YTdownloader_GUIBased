  import os
import tkinter as tk
from tkinter import ttk, messagebox
from pytube import YouTube
import threading
from queue import Queue, Empty

class VideoDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video Downloader")
        self.geometry("500x350")

        self.url_label = ttk.Label(self, text="Enter YouTube URL:")
        self.url_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.url_entry = ttk.Entry(self, width=50)
        self.url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="we")

        self.quality_label = ttk.Label(self, text="Select Quality:")
        self.quality_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.quality_buttons_frame = ttk.Frame(self)
        self.quality_buttons_frame.grid(row=1, column=1, padx=10, pady=10, sticky="we")

        qualities = ["144p", "240p", "360p", "480p", "720p", "1080p", "Highest"]
        self.quality_buttons = [ttk.Button(self.quality_buttons_frame, text=quality, command=lambda q=quality: self.set_quality(q)) for quality in qualities]
        for i, button in enumerate(self.quality_buttons):
            button.grid(row=0, column=i, padx=5, pady=5)

        self.filename_label = ttk.Label(self, text="Enter Filename (optional):")
        self.filename_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        self.filename_entry = ttk.Entry(self, width=50)
        self.filename_entry.grid(row=2, column=1, padx=10, pady=10, sticky="we")

        self.size_check_var = tk.BooleanVar()
        self.size_check = ttk.Checkbutton(self, text="Check file size before downloading", variable=self.size_check_var)
        self.size_check.grid(row=3, columnspan=2, padx=10, pady=10, sticky="w")

        self.download_button = ttk.Button(self, text="Download", command=self.start_download)
        self.download_button.grid(row=4, columnspan=2, padx=10, pady=10, sticky="we")

        self.cancel_button = ttk.Button(self, text="Cancel", command=self.cancel_download)
        self.cancel_button.grid(row=5, columnspan=2, padx=10, pady=10, sticky="we")
        self.cancel_button.config(state="disabled")

        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=6, columnspan=2, padx=10, pady=10, sticky="we")

        self.quality = "Highest"
        self.queue = Queue()
        self.running = False
        self.cancelled = False

    def set_quality(self, quality):
        self.quality = quality

    def start_download(self):
        if self.running:
            messagebox.showinfo("Download In Progress", "A download is already in progress.")
            return

        url = self.url_entry.get()
        filename = self.filename_entry.get().strip()
        check_size = self.size_check_var.get()

        self.running = True
        self.cancelled = False
        self.download_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        download_thread = threading.Thread(target=self.download_video, args=(url, filename, check_size))
        download_thread.start()
        self.after(100, self.check_queue)

    def cancel_download(self):
        if not self.running:
            messagebox.showinfo("No Download in Progress", "No download is currently in progress.")
            return

        self.cancelled = True
        self.download_button.config(state="normal")
        self.cancel_button.config(state="disabled")

    def check_queue(self):
        try:
            msg = self.queue.get(0)
            if msg == "Download Complete":
                self.running = False
                self.download_button.config(state="normal")
                self.cancel_button.config(state="disabled")
            elif msg.startswith("Error"):
                messagebox.showerror("Error", msg)
                self.running = False
                self.download_button.config(state="normal")
                self.cancel_button.config(state="disabled")
            elif msg.startswith("Progress:"):
                progress = float(msg.split(":")[1])
                self.progress_bar["value"] = progress
            self.queue.task_done()
            self.after(100, self.check_queue)
        except Empty:
            if self.running:
                self.after(100, self.check_queue)

    def download_video(self, url, filename, check_size):
        try:
            yt = YouTube(url, on_progress_callback=self.progress_callback)
            stream = None
            if self.quality == "Highest":
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            else:
                stream = yt.streams.filter(resolution=self.quality).first()

            if check_size:
                expected_size = stream.filesize
                response = messagebox.askyesno("Expected File Size", f"Expected File Size: {expected_size / (1024*1024):.2f} MB\nDo you want to continue?")
                if not response:
                    self.queue.put("Download Complete")
                    return

            default_download_path = os.path.join(os.path.expanduser('~'), 'Downloads')

            if not filename:
                filename = self.generate_filename(yt.title, default_download_path)
            else:
                full_filename = os.path.join(default_download_path, filename)
                if os.path.exists(full_filename):
                    response = messagebox.askyesno("File Exists", f"A file named '{filename}' already exists. Do you want to overwrite it?")
                    if not response:
                        self.queue.put("Download Complete")
                        return

            stream.download(output_path=default_download_path, filename=filename)

            if not self.cancelled:
                self.queue.put("Download Complete")
            else:
                os.remove(os.path.join(default_download_path, filename))
                self.queue.put("Download Cancelled")
        except Exception as e:
            self.queue.put(f"Error occurred: {e}")

    def generate_filename(self, video_title, download_path):
        filename = video_title + ".mp4"
        index = 1
        while os.path.exists(os.path.join(download_path, filename)):
            filename = f"{video_title}_{index}.mp4"
            index += 1
        return filename

    def progress_callback(self, stream, chunk, bytes_remaining):
        total_bytes = stream.filesize
        bytes_downloaded = total_bytes - bytes_remaining
        progress = (bytes_downloaded / total_bytes) * 100
        self.queue.put(f"Progress:{progress}")

if __name__ == "__main__":
    app = VideoDownloaderApp()
    app.mainloop()
