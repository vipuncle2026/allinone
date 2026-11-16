#!/bin/bash
set -e

# ── All-in-One 桌面端一键构建脚本 ───────────────────────
# 用法: bash build-mac.sh [后缀]
#   无参数      -> AllInOne-<版本>-arm64.dmg
#   带后缀      -> AllInOne-<版本>-arm64-<后缀>.dmg
#   环境变量 KEEP_OLD=1 时不覆盖同名旧包，自动追加时间戳
# 产出: electron/release/*.dmg

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
ELECTRON_DIR="$SCRIPT_DIR"
APP_VERSION="$(node -p "require('$ELECTRON_DIR/package.json').version")"

# ── 环境修复 ──
export NODE_OPTIONS=""
export ELECTRON_MIRROR="${ELECTRON_MIRROR:-https://npmmirror.com/mirrors/electron/}"

echo "========================================="
echo "  All-in-One 桌面端 macOS 构建"
echo "========================================="

# ── 1. 检查 Python venv ─────────────────────────────
echo ""
echo "[1/5] 检查 Python venv..."
PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
if [ ! -f "$PYTHON_BIN" ] || ! "$PYTHON_BIN" --version &>/dev/null; then
    echo "  修复 venv shebang..."
    SYS_PYTHON="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14"
    if [ -f "$SYS_PYTHON" ]; then
        for f in "$BACKEND_DIR/venv/bin/"*; do
            if [ -f "$f" ] && head -1 "$f" | grep -q "^#!"; then
                sed -i '' "1s|^#!.*|#!$SYS_PYTHON|" "$f"
            fi
        done
        echo "  已修复 venv shebang"
    else
        echo "  错误: 找不到系统 Python 3.14"
        exit 1
    fi
fi
echo "  Python: $($PYTHON_BIN --version)"

# ── 2. PyInstaller 打包后端 ─────────────────────────
echo ""
echo "[2/5] PyInstaller 打包后端 API..."
cd "$BACKEND_DIR"

if ! "$PYTHON_BIN" -m PyInstaller --version &>/dev/null; then
    echo "  安装 PyInstaller 到 venv..."
    "$PYTHON_BIN" -m pip install --target "$BACKEND_DIR/venv/lib/python3.14/site-packages" pyinstaller -q
fi

if [ -d "$BACKEND_DIR/dist/allinone-api" ]; then
    # 用 mv 移走旧产物（避免 PyInstaller 内部删除触发批量删除保护）
    STALE_DIR="/tmp/allinone-api-stale-$(date +%s)"
    mkdir -p "$STALE_DIR"
    mv "$BACKEND_DIR/dist/allinone-api" "$STALE_DIR/"
    echo "  旧产物已移出: $STALE_DIR"
fi
"$PYTHON_BIN" -m PyInstaller allinone-api.spec --distpath dist --workpath build_temp -y
echo "  后端打包完成: $BACKEND_DIR/dist/allinone-api/"

# ── 3. 构建前端 ─────────────────────────────────────
echo ""
echo "[3/5] 构建前端 dist..."
cd "$FRONTEND_DIR"
npm run build
echo "  前端构建完成: $FRONTEND_DIR/dist/"

# ── 4. electron-builder 打包 .app（target=dir，跳过 dmg 下载）──
echo ""
echo "[4/5] electron-builder 构建 .app..."
cd "$ELECTRON_DIR"

# 备份 package.json
cp package.json package.json.bak

# 用 node 脚本临时修改 target 为 dir
node -e "
const fs = require('fs');
const d = JSON.parse(fs.readFileSync('package.json','utf8'));
d.build.mac.target = 'dir';
delete d.build.dmg;
fs.writeFileSync('package.json', JSON.stringify(d, null, 2));
"

"$ELECTRON_DIR/node_modules/.bin/electron-builder" --mac

# 恢复 package.json
mv package.json.bak package.json

echo "  .app 构建完成: $ELECTRON_DIR/release/mac-arm64/AllInOne.app"

# ── 5. 手动打包 DMG（hdiutil）───────────────────────
echo ""
echo "[5/5] hdiutil 打包 DMG..."

DMG_SUFFIX="$1"
VOLUME_NAME="AllInOne"
if [ -n "$DMG_SUFFIX" ]; then
  DMG_NAME="AllInOne-${APP_VERSION}-arm64-${DMG_SUFFIX}.dmg"
  VOLUME_NAME="AllInOne-${DMG_SUFFIX}"
else
  DMG_NAME="AllInOne-${APP_VERSION}-arm64.dmg"
fi

DMG_PATH="$ELECTRON_DIR/release/$DMG_NAME"

# 不覆盖旧包：已存在则追加时间戳
if [ -f "$DMG_PATH" ] && [ "${KEEP_OLD:-0}" = "1" ]; then
  DMG_PATH="${DMG_PATH%.dmg}-$(date +%Y%m%d-%H%M).dmg"
fi

echo "  输出文件: $(basename "$DMG_PATH")"

DMG_STAGING="/tmp/allinone-dmg-$$"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"

cp -R "$ELECTRON_DIR/release/mac-arm64/AllInOne.app" "$DMG_STAGING/"
ln -sf /Applications "$DMG_STAGING/Applications"

rm -f "$DMG_PATH"

hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$DMG_STAGING" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

# 清理临时目录
rm -rf "$DMG_STAGING"

echo ""
echo "========================================="
echo "  构建完成！"
echo "  DMG 文件位于: $ELECTRON_DIR/release/"
ls -lh "$ELECTRON_DIR/release/"*.dmg
echo "========================================="
