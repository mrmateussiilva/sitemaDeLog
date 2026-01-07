import os
import time
import threading
import queue
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from zig_bridge import ZigBackend


class LogFileHandler(FileSystemEventHandler):
    """
    Manipulador de eventos do watchdog.
    Responsável por reagir a novos arquivos na pasta monitorada.
    """

    def __init__(self, watcher: "LogWatcher"):
        super().__init__()
        self.watcher = watcher

    def on_created(self, event):
        # Ignorar diretórios
        if event.is_directory:
            return

        path = Path(event.src_path)
        # Filtrar extensões suportadas
        ext = path.suffix.lower()
        if ext not in {".html", ".htm", ".csv"}:
            return

        self.watcher._log(f"Novo arquivo detectado: {path.name}")
        self.watcher.enqueue_file(path)


class LogWatcher:
    """
    Watcher de arquivos para monitorar uma pasta de origem e processar
    automaticamente arquivos HTML/CSV assim que forem criados.

    - Monitoramento NÃO recursivo (apenas a pasta de origem)
    - Espera o arquivo estabilizar (tamanho não muda) antes de processar
    - Para cada arquivo: gera JSON individual na pasta de destino
    - Usa ZigBackend.processar_html / processar_csv conforme extensão
    - Envia logs via callback (ex: LogManagerApp.log_message)
    """

    def __init__(self, origem: str, destino: str, log_callback=None):
        self.origem = Path(origem)
        self.destino = Path(destino)
        self.log_callback = log_callback

        self.backend = ZigBackend()

        self._queue: "queue.Queue[Path]" = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        self._observer: Observer | None = None

    # ------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------
    def start(self):
        """Inicia o watcher e a thread de processamento."""
        if self._observer is not None:
            # Já está rodando
            return

        if not self.origem.exists():
            raise FileNotFoundError(f"Diretório de origem não existe: {self.origem}")

        self.destino.mkdir(parents=True, exist_ok=True)

        self._log(f"Iniciando monitoramento em: {self.origem}")
        event_handler = LogFileHandler(self)
        self._observer = Observer()
        # Monitorar APENAS a pasta (não recursivo)
        self._observer.schedule(event_handler, str(self.origem), recursive=False)
        self._observer.start()

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop, name="LogWatcherWorker", daemon=True
        )
        self._worker_thread.start()

    def stop(self):
        """Interrompe o watcher e a thread de processamento."""
        self._log("Parando monitoramento...")

        # Parar observer
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=5)
            except Exception:
                pass
            self._observer = None

        # Parar worker thread
        self._stop_event.set()
        # Inserir sentinela para destravar queue
        try:
            self._queue.put_nowait(None)  # type: ignore[arg-type]
        except Exception:
            pass

        if self._worker_thread is not None:
            try:
                self._worker_thread.join(timeout=5)
            except Exception:
                pass
            self._worker_thread = None

        self._log("Monitoramento parado.")

    def enqueue_file(self, path: Path):
        """Enfileira arquivo para processamento assíncrono."""
        try:
            self._queue.put_nowait(path)
        except Exception as exc:
            self._log(f"Erro ao enfileirar arquivo {path.name}: {exc}")

    # ------------------------------------------------------------
    # Loop de processamento
    # ------------------------------------------------------------
    def _worker_loop(self):
        """Loop da thread que processa arquivos enfileirados."""
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is None:
                # Sentinela para encerrar
                break

            try:
                self._process_file(item)
            except Exception as exc:
                self._log(f"Erro ao processar {item.name}: {exc}")
            finally:
                self._queue.task_done()

    # ------------------------------------------------------------
    # Processamento de arquivo individual
    # ------------------------------------------------------------
    def _process_file(self, path: Path):
        """Processa um único arquivo após estabilizar o tamanho."""
        if not path.exists():
            self._log(f"Arquivo desapareceu antes do processamento: {path.name}")
            return

        # Esperar arquivo estabilizar
        if not self._wait_for_stable_file(path):
            self._log(f"Timeout aguardando arquivo estabilizar: {path.name}")
            return

        ext = path.suffix.lower()
        nome_base = path.stem
        destino_json = self.destino / f"{nome_base}.json"

        self._log(f"Processando arquivo: {path.name}")

        if ext in {".html", ".htm"}:
            ok = self.backend.processar_html(str(path), str(destino_json))
        elif ext == ".csv":
            ok = self.backend.processar_csv(str(path), str(destino_json))
        else:
            self._log(f"Extensão não suportada: {ext}")
            return

        if ok:
            self._log(f"✓ JSON gerado: {destino_json.name}")
        else:
            self._log(f"✗ Erro ao processar arquivo: {path.name}")

    def _wait_for_stable_file(self, path: Path, timeout: float = 30.0, interval: float = 0.5) -> bool:
        """
        Aguarda até que o tamanho do arquivo fique estável,
        indicando que a escrita foi concluída.
        """
        self._log(f"Aguardando arquivo estabilizar: {path.name}")
        start = time.time()
        last_size = -1

        while time.time() - start < timeout:
            try:
                size = path.stat().st_size
            except FileNotFoundError:
                # Arquivo removido durante a espera
                return False

            if size == last_size and size > 0:
                # Tamanho estável e não-zero
                self._log(f"Arquivo estabilizado ({size} bytes): {path.name}")
                return True

            last_size = size
            time.sleep(interval)

        return False

    # ------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------
    def _log(self, msg: str):
        """Envia mensagem para callback de log, se existir."""
        if self.log_callback is not None:
            try:
                self.log_callback(msg)
            except Exception:
                # Evitar que erros de UI quebrem o watcher
                pass
        else:
            # Fallback para debug em console
            print(f"[LogWatcher] {msg}")


