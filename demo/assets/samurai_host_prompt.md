# SAMURAI 進行役画像

生成方法：組み込み image_gen（imagegen スキル）。
参照画像：`jin_samurai_character.png`。
出力：`samurai_host_atlas.png`（透明背景、3列×2行）。元の画像は保持。
表示時に各セルを切り出し、元の縦横比で描画する。

## 使用したプロンプト

Use case: identity-preserve. Create ONE production sprite atlas for a scientific instrument exhibition UI host, based on the provided reference character SAMURAI. Preserve his adult masculine face, black high ponytail tied with red cord, black Japanese armor with restrained red accents, handsome serious anime ink-painting appearance. The reference is the character identity source, not a poster layout. Output a single square PNG sprite atlas, exactly 3 columns by 2 rows of equally sized cells. Each cell contains one waist-up portrait, centered with safe margins, consistent scale and straight-on/three-quarter perspective, no overlap across cells. Row-major order: 1 welcoming warm slight smile with open palm greeting; 2 focused thoughtful expression, hand on chin; 3 determined concentrated expression, clenched fist near chest encouraging progress; 4 friendly instructive expression pointing to viewer's right toward the charts; 5 satisfied broad smile, restrained celebratory fist raised; 6 serious concerned calm expression with open palm stop gesture. Six visibly distinct faces and gestures, same person and outfit. Truly transparent background in all cells, no ground, no panel borders, no shadows outside silhouette, NO text, NO letters, NO logos, NO sword, no extra characters. High-quality crisp detailed expressive illustration legible at 250px display size. Deliver only the atlas.
