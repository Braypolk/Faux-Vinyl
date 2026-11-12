FROM golang:1.27.3-bookworm AS build
WORKDIR /src
COPY . /src
RUN CGO_ENABLED=1 go build -trimpath -tags netgo,osusergo -ldflags="-s -w" -o /fauxvinyl .

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /fauxvinyl /usr/local/bin/fauxvinyl
COPY --from=build /src/static /app/static
ENV DATA_DIR=/data GOMEMLIMIT=96MiB GOGC=50
USER 1000:1000
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=4 CMD ["fauxvinyl", "-healthcheck"]
ENTRYPOINT ["fauxvinyl"]
