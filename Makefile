.PHONY: help build up down logs clean restart dev

help: ## Bu yardım mesajını göster
	@echo "Basit Chat Uygulaması Komutları:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Docker image'ını build et
	docker-compose build

up: ## Uygulamayı başlat
	docker-compose up -d

down: ## Uygulamayı durdur
	docker-compose down

logs: ## Logları göster
	docker-compose logs -f

clean: ## Tüm container ve volume'leri temizle
	docker-compose down -v --remove-orphans
	docker system prune -f

restart: ## Uygulamayı yeniden başlat
	docker-compose restart

dev: ## Development modunda başlat
	docker-compose up

# Health check
health: ## Uygulamanın sağlık durumunu kontrol et
	@echo "Chat uygulaması kontrol ediliyor..."
	@curl -f http://localhost:8000/ && echo "✅ Chat app çalışıyor" || echo "❌ Chat app çalışmıyor"

