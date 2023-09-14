# ai-cat-api
[![ci](https://github.com/nekochans/ai-cat-api/actions/workflows/ci.yml/badge.svg)](https://github.com/nekochans/ai-cat-api/actions/workflows/ci.yml)
[![deploy to staging](https://github.com/nekochans/ai-cat-api/actions/workflows/deploy-to-staging.yml/badge.svg)](https://github.com/nekochans/ai-cat-api/actions/workflows/deploy-to-staging.yml)
[![deploy to production](https://github.com/nekochans/ai-cat-api/actions/workflows/deploy-to-production.yml/badge.svg)](https://github.com/nekochans/ai-cat-api/actions/workflows/deploy-to-production.yml)

ねこの人格を持ったAIとお話できるサービスのバックエンドAPI

## Getting Started

MacOSを利用する前提の手順になります。

### 環境変数の設定

環境変数の設定を行います。

[direnv](https://github.com/direnv/direnv) を利用すると既存の環境変数に影響を与えないので便利です。

```bash
export OPENAI_API_KEY=OpenAIのAPIキーを指定
export API_CREDENTIAL=任意の文字列を指定
export DB_HOST=PlanetScaleのデータベースホスト名を指定
export DB_NAME=PlanetScaleのデータベース名を指定
export DB_USERNAME=PlanetScaleのデータベースユーザー名を指定
export DB_PASSWORD=PlanetScaleのデータベースパスワードを指定
export SSL_CERT_PATH=`SSL_CERT_PATH` についてを参照
```

#### `SSL_CERT_PATH` について

`SSL_CERT_PATH` はSSL証明書のパスを指定します。

以下のコマンドで証明書の場所を特定出来ます。

```bash
openssl version -d
```

筆者の環境だと以下のような結果が表示されました。

```
OPENSSLDIR: "/private/etc/ssl"
```

`/private/etc/ssl/cert.pem` というファイルがあったので以下の通りに指定しています。

```bash
export SSL_CERT_PATH=/private/etc/ssl/cert.pem
```

### Pythonのインストール（既にインストールされている場合は省略可）

利用するPythonのバージョンは `Dockerfile` に記載してあります。

標準でインストールされているPythonではなくプロジェクト毎にバージョン管理出来る状態が理想です。

[asdf](https://asdf-vm.com/) を使ってプロジェクト用にPythonをインストール手順を記載します。

1. [asdf](https://asdf-vm.com/) をインストールします

```bash
brew install asdf
```

2. [asdf](https://asdf-vm.com/) のPythonPluginを追加します

```bash
asdf plugin add python
```

3. `Dockerfile` に記載してあるバージョンのPythonをインストール

```bash
asdf install python {`Dockerfile` に記載してあるバージョンを指定}
```

4. プロジェクトルートで利用するPythonのバージョンを指定

```bash
asdf local python {`Dockerfile` に記載してあるバージョンを指定}
```

### Poetryのインストール

Homebrew でインストールを実施します。

```bash
brew install poetry
```

下記は必須ではありませんが、以下を実行するとプロジェクト配下に仮想環境が作成されるようになるので分かりやすいです。

```bash
poetry config virtualenvs.in-project true
```

Poetryの設定に関しては以下で現在値を確認可能です。

```bash
poetry config --list
```

### 依存packageのインストール & 仮想環境の作成

以下を実行します。

```bash
poetry install
```

### 仮想環境のアクティベート

以下を実行します。

```bash
poetry shell
```

packageの追加や Makefile 内のタスクを実行する為には仮想環境がアクティベート状態である必要があります。

### アプリケーションサーバーの起動

仮想環境がアクティベートされた状態で以下を実行します。

```bash
make run
```

以下で動作確認が可能です。

```bash
curl -v -N \
-X POST \
-H "Content-Type: application/json" \
-H "Authorization: Basic $API_CREDENTIAL" \
-H "Accept: text/event-stream" \
-d '
{
  "userId": "6a17f37c-996e-7782-fefd-d71eb7eaaa37",
  "message": "こんにちはもこちゃん🐱"
}' \
http://0.0.0.0:8000/cats/moko/streaming-messages
```

### コンテナでの起動方法

```bash
# Build
docker build -t ai-cat-api .

# コンテナを起動
docker container run -d -p 5002:5000 -e OPENAI_API_KEY=$OPENAI_API_KEY -e API_CREDENTIAL=$API_CREDENTIAL -e DB_HOST=$DB_HOST -e DB_NAME=$DB_NAME -e DB_USERNAME=$DB_USERNAME -e DB_PASSWORD=$DB_PASSWORD ai-cat-api

## コンテナの中に入りたい場合は↓のようにする
docker exec -it {コンテナIDを指定} bash
```

以下のようにコンテナに対してHTTPリクエストを送信する事で動作確認を実施します。

```bash
curl -v -N \
-X POST \
-H "Content-Type: application/json" \
-H "Authorization: Basic $API_CREDENTIAL" \
-H "Accept: text/event-stream" \
-d '
{
  "userId": "6a17f37c-996e-7782-fefd-d71eb7eaaa37",
  "message": "こんにちはもこちゃん🐱"
}' \
http://localhost:5002/cats/moko/streaming-messages
```

## デプロイについて

本アプリケーションは https://fly.io でホスティングされています。

ステージングと本番の2つの環境が存在します。

`main` にPRがマージされるとステージング環境にデプロイされます。

本番環境へのデプロイは https://github.com/nekochans/ai-cat-api/releases から新しいリリースページを作成する事で実行されます。

ロールバックの際は [本番用のデプロイワークフロー](https://github.com/nekochans/ai-cat-api/actions/workflows/deploy-to-production.yml) を手動実行する事になりますが、その際にGitタグがあると前のバージョンに戻しやすいので必ず作成します。

別サービスのドキュメントですが [lgtm-cat-ui 5. リリースページの作成](https://github.com/nekochans/lgtm-cat-ui/blob/main/.github/CONTRIBUTING.md#5-%E3%83%AA%E3%83%AA%E3%83%BC%E3%82%B9%E3%83%9A%E3%83%BC%E3%82%B8%E3%81%AE%E4%BD%9C%E6%88%90) と手順は同じです。
