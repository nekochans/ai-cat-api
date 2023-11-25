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
API_CREDENTIAL=`echo -n "$BASIC_AUTH_USERNAME:$BASIC_AUTH_PASSWORD" | base64`
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
http://0.0.0.0:8000/cats/moko/messages-for-guest-users
```

## 各コマンドの説明

`poetry shell` で仮想環境をアクティベートした状態で利用出来る様々なコマンドを解説します。

### Linterを実行

```bash
make lint
```

### Formatterを実行

```bash
make format
```

### テストコードの実行

```bash
make test
```

### typecheckの実行

```bash
make typecheck
```

## Dockerによる環境構築

[Docker Desktop](https://www.docker.com/products/docker-desktop/) もしくは [OrbStack](https://orbstack.dev/) がインストールされている場合はDockerによる環境構築も可能です。

以下のコマンドでコンテナを起動します。

```bash
docker compose up --build -d
```

※ 2回目以降は `docker compose up -d` だけで大丈夫です。

以下のコマンドを実行してSSEのレスポンスが返ってくれば正常動作しています。

```bash
API_CREDENTIAL=`echo -n "$BASIC_AUTH_USERNAME:$BASIC_AUTH_PASSWORD" | base64`
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
http://localhost:5002/cats/moko/messages-for-guest-users
```

コンテナの中に入る場合は以下を実行します。

```bash
docker compose exec ai-cat-api bash
```

これでコンテナ内でテスト等のコマンドを実行可能です。

### コンテナ内での `make` コマンド利用の注意点

一点注意点があります。

コンテナ内のカレントディレクトリは `/src` になっています。

その為、ここで `make test` 等を実行しても上手く行きません。

以下のコマンドで `/` に移動します。

```bash
cd /
```

その上で `make test` 等を実行する必要があります。

これは結構面倒だと思うのでコンテナ内で各タスクを実行する為のタスクを用意しました。

```bash
# コンテナ内でLinterを実行
make lint-container

# コンテナ内でFormatterを実行
make format-container

# コンテナ内でテストコードを実行
make test-container

# コンテナ内でtypecheckを実行
make run-token-creator-container
```

### コンテナ内のMySQLに接続する

以下で接続が可能です。

```bash
mysql -u root -h 127.0.0.1 -p -P 33060
```

パスワードは `docker-compose.yml` の `MYSQL_ROOT_PASSWORD` に記載してある値です。

### コンテナの停止

以下でコンテナを停止します。

```bash
docker compose down
```

もしも `Dockerfile` や `docker-compose.yml` に変更があった場合は以下のコマンドでコンテナを完全に廃棄してから再度 `docker compose up --build -d` を実行するようにお願いします。

```bash
docker compose down --rmi all --volumes --remove-orphans
```

## デプロイについて

本アプリケーションは https://fly.io でホスティングされています。

ステージングと本番の2つの環境が存在します。

`main` にPRがマージされるとステージング環境にデプロイされます。

本番環境へのデプロイは https://github.com/nekochans/ai-cat-api/releases から新しいリリースページを作成する事で実行されます。

ロールバックの際は [本番用のデプロイワークフロー](https://github.com/nekochans/ai-cat-api/actions/workflows/deploy-to-production.yml) を手動実行する事になりますが、その際にGitタグがあると前のバージョンに戻しやすいので必ず作成します。

別サービスのドキュメントですが [lgtm-cat-ui 5. リリースページの作成](https://github.com/nekochans/lgtm-cat-ui/blob/main/.github/CONTRIBUTING.md#5-%E3%83%AA%E3%83%AA%E3%83%BC%E3%82%B9%E3%83%9A%E3%83%BC%E3%82%B8%E3%81%AE%E4%BD%9C%E6%88%90) と手順は同じです。
