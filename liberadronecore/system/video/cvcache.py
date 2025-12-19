import os
from collections import OrderedDict

import numpy as np

try:
    import cv2
except ImportError as e:
    raise ImportError(
        "OpenCV (cv2) が見つかりません。\n"
        "BlenderのPythonに opencv-python を入れてください。\n"
        "例: <blender_python> -m pip install opencv-python"
    ) from e


class FrameSampler:
    """
    - Movie/Videoから指定フレームを画像として取り出し
    - 任意のキャッシュ戦略で保持
    - UV(x,y) サンプリング
    """
    def __init__(
        self,
        path: str,
        cache_mode: str = "lru",   # "none" | "lru" | "full"
        lru_max: int = 32,
        resize_to=None,            # (w, h) or None
        output_dtype=np.uint8,     # uint8 推奨（省メモリ）
        store_rgba=True,           # True: RGBA / False: RGB
        memmap_path=None,          # cache_mode="full" でRAMに乗せたくないなら指定
    ):
        self.path = os.path.abspath(path)
        self.cache_mode = cache_mode
        self.lru_max = max(1, int(lru_max))
        self.resize_to = resize_to
        self.output_dtype = output_dtype
        self.store_rgba = store_rgba
        self.memmap_path = memmap_path

        if not os.path.exists(self.path):
            raise FileNotFoundError(self.path)

        self.cap = cv2.VideoCapture(self.path)
        if not self.cap.isOpened():
            raise RuntimeError(f"VideoCapture open failed: {self.path}")

        # 動画情報
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS)) or 0.0

        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
        if self.resize_to is not None:
            self.width, self.height = int(self.resize_to[0]), int(self.resize_to[1])
        else:
            self.width, self.height = w, h

        self.channels = 4 if self.store_rgba else 3

        # LRU cache
        self._lru = OrderedDict()

        # FULL cache（必要なら後で build_full_cache）
        self._full = None  # np.ndarray or np.memmap

        if self.cache_mode == "full":
            self.build_full_cache()

    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    # --------------------------
    # デコード & 変換
    # --------------------------
    def _decode_frame_bgr(self, frame_index: int):
        if self.frame_count > 0:
            frame_index = max(0, min(frame_index, self.frame_count - 1))
        else:
            frame_index = max(0, frame_index)

        # OpenCVのフレーム番号は 0-based
        ok = self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        # setが効かないコーデックもある（その場合 read 失敗しがち）
        ret, bgr = self.cap.read()
        if not ret or bgr is None:
            raise RuntimeError(f"Failed to read frame: {frame_index}")

        if self.resize_to is not None:
            bgr = cv2.resize(bgr, self.resize_to, interpolation=cv2.INTER_AREA)

        return bgr

    def _bgr_to_out(self, bgr: np.ndarray) -> np.ndarray:
        # BGR -> RGB(A)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        if self.store_rgba:
            a = np.full((rgb.shape[0], rgb.shape[1], 1), 255, dtype=rgb.dtype)
            out = np.concatenate([rgb, a], axis=2)
        else:
            out = rgb

        if self.output_dtype == np.float32:
            # 0..1 float
            out = out.astype(np.float32) / 255.0
        elif self.output_dtype == np.uint8:
            # 0..255
            out = out.astype(np.uint8, copy=False)
        else:
            out = out.astype(self.output_dtype)

        return out

    # --------------------------
    # キャッシュ
    # --------------------------
    def build_full_cache(self):
        if self.frame_count <= 0:
            raise RuntimeError("frame_count is unknown/0. full cache is not supported for this source.")

        shape = (self.frame_count, self.height, self.width, self.channels)

        if self.memmap_path:
            mm_path = os.path.abspath(self.memmap_path)
            os.makedirs(os.path.dirname(mm_path), exist_ok=True)
            full = np.memmap(mm_path, mode="w+", dtype=self.output_dtype, shape=shape)
        else:
            full = np.empty(shape, dtype=self.output_dtype)

        # 連続readが一番安定＆速いので、POS_FRAMESを毎回setしない
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        for f in range(self.frame_count):
            ret, bgr = self.cap.read()
            if not ret or bgr is None:
                raise RuntimeError(f"Failed to read frame during full cache build: {f}")

            if self.resize_to is not None:
                bgr = cv2.resize(bgr, self.resize_to, interpolation=cv2.INTER_AREA)

            full[f] = self._bgr_to_out(bgr)

        self._full = full
        # FULLを作った後もランダムアクセス用にcapは残してOK（必要ならcloseしてもいい）

    def _lru_get(self, key):
        if key in self._lru:
            self._lru.move_to_end(key)
            return self._lru[key]
        return None

    def _lru_put(self, key, value):
        self._lru[key] = value
        self._lru.move_to_end(key)
        while len(self._lru) > self.lru_max:
            self._lru.popitem(last=False)

    # --------------------------
    # API：フレーム取得 & サンプリング
    # --------------------------
    def get_frame(self, frame_index: int) -> np.ndarray:
        # FULL
        if self._full is not None:
            return self._full[frame_index]

        # LRU
        if self.cache_mode == "lru":
            cached = self._lru_get(frame_index)
            if cached is not None:
                return cached

        # decode
        bgr = self._decode_frame_bgr(frame_index)
        out = self._bgr_to_out(bgr)

        if self.cache_mode == "lru":
            self._lru_put(frame_index, out)

        return out

    def sample_uv(self, frame_index: int, u: float, v: float, clamp=True):
        """
        u,v: 0..1 (左下原点想定なら v を反転するか選べる)
        ここでは画像座標として「左上が(0,0)」の扱いにしているので
        vは上から下に増える想定（BlenderのUVに合わせたいなら v=1-v して呼ぶと良い）
        """
        img = self.get_frame(frame_index)
        h, w = img.shape[0], img.shape[1]

        if clamp:
            u = 0.0 if u < 0 else 1.0 if u > 1 else u
            v = 0.0 if v < 0 else 1.0 if v > 1 else v

        x = int(u * (w - 1))
        y = int(v * (h - 1))
        return img[y, x]  # [R,G,B,(A)] uint8 or float

    def sample_xy(self, frame_index: int, x: int, y: int, clamp=True):
        img = self.get_frame(frame_index)
        h, w = img.shape[0], img.shape[1]
        if clamp:
            x = 0 if x < 0 else (w - 1 if x >= w else x)
            y = 0 if y < 0 else (h - 1 if y >= h else y)
        return img[y, x]
sampler = FrameSampler(
    path="F:/footage/test.mp4",
    cache_mode="lru",      # まずはこれが強い
    lru_max=64,
    resize_to=(640, 360),  # サンプリング用途なら縮小が超効く
    output_dtype=np.uint8, # 省メモリ & 速い
    store_rgba=True
)

# フレーム100のUV(0.2, 0.7)を読む
rgba = sampler.sample_uv(100, 0.2, 0.7)
print(rgba)

# 終わったら
sampler.close()