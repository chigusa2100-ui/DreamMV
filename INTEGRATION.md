# 既存コードへの組み込み

## 1. ProjectQueueService に追加するメソッド（要調整）

`RenderWorker` は `queue.set_scene_status(scene_id, status, error=None, output=None)` を呼びます。
既存のキューJSONの構造に合わせて実装してください。イメージ:

```python
def set_scene_status(self, scene_id, status, error=None, output=None):
    data = self.load()
    for s in data.get("scenes", []):
        if s.get("id") == scene_id:
            s["status"] = status
            s["error"] = error
            if output:
                s["output"] = output
    self.save(data)   # ← 既存の保存メソッド名に合わせる
```

## 2. main.py (DreamMV クラス) の変更

import に追加:

```python
import json
from src.dreammv.render_worker import RenderWorker
```

`__init__` のボタン作成部に追加:

```python
self.render_button = QPushButton("🌙 Wanでレンダリング開始")
self.render_button.setEnabled(False)
self.render_button.clicked.connect(self.start_render)
self.render_log = QLabel("")
layout.addWidget(self.render_button)   # layout = QVBoxLayout(self) の後
layout.addWidget(self.render_log)
self.worker: RenderWorker | None = None
```

`refresh_queue()` 内、`self.retry_button.setEnabled(failed > 0)` の後に追加:

```python
self.render_button.setEnabled(self.queue_service is not None and (queued + failed) > 0)
```

メソッドを追加:

```python
def start_render(self):
    if self.queue_service is None or not self.selected_path or self.worker:
        return
    settings_path = Path.cwd() / "wan_settings.json"
    s = json.loads(settings_path.read_text("utf-8")) if settings_path.exists() else {}
    self.worker = RenderWorker(
        self.queue_service, self.project_dir, Path(self.selected_path),
        preset=s.get("preset", "light"), models_dir=s.get("models_dir"),
    )
    self.worker.log.connect(self.render_log.setText)
    self.worker.scene_changed.connect(self.refresh_queue)
    self.worker.finished_ok.connect(self._render_done)
    self.worker.failed.connect(self._render_failed)
    self.render_button.setEnabled(False)
    self.worker.start()

def _render_done(self, path):
    self.worker = None
    self.render_log.setText(f"完成: {path}")
    QMessageBox.information(self, "完成", f"ミュージックビデオを書き出しました。\n{path}")

def _render_failed(self, msg):
    self.worker = None
    self.render_log.setText(f"失敗: {msg}")
    QMessageBox.critical(self, "レンダリングエラー", msg)
```

既存の「失敗シーンを再試行」→「レンダリング開始」の順で押せば、失敗分だけ再生成されます。

## 3. ビルド手順

1. プロジェクトルートに `main.py`（エントリポイント）が無ければ名前を `DreamMV.iss` 内の `main.py` に合わせる
2. この zip の `src/dreammv/` を既存の `src/dreammv/` にコピー
3. `installer/DreamMV.iss` を Inno Setup 6 で開いて Compile → `installer/Output/DreamMV-Setup.exe`
