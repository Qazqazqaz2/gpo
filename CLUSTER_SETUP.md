# Настройка и использование кластерного решения

Данное руководство описывает настройку и использование кластерного решения для балансировки нагрузки между несколькими серверами.

## Архитектура решения

Кластерное решение состоит из следующих компонентов:

1. **Серверы приложения** - несколько экземпляров приложения Flask, работающих на разных портах
2. **Обратный прокси** - компонент, который распределяет запросы между серверами приложения
3. **Менеджер кластера** - скрипт для запуска и управления всеми компонентами

### Алгоритмы балансировки нагрузки

Поддерживаются следующие алгоритмы балансировки нагрузки:

- **Round Robin** - запросы распределяются последовательно между серверами
- **Least Connections** - запросы направляются на сервер с наименьшим количеством активных соединений
- **IP Hash** - запросы от одного IP-адреса всегда направляются на один и тот же сервер

## Требования

- Python 3.7 или выше
- Установленные зависимости из файла requirements.txt

## Установка

1. Убедитесь, что у вас установлены все необходимые зависимости:

```bash
pip install -r requirements.txt
```

## Запуск кластера

### Простой запуск

Для запуска кластера с настройками по умолчанию выполните:

```bash
python run_cluster.py
```

Это запустит:
- 2 экземпляра сервера на портах 5000 и 5001
- Обратный прокси на порту 8000 с алгоритмом Round Robin

### Расширенные настройки

Вы можете настроить кластер с помощью следующих параметров:

```bash
python run_cluster.py --nodes 3 --base-port 5000 --proxy-port 8080 --algorithm least_connections --sticky-sessions
```

Параметры:
- `--nodes` или `-n`: количество серверов (по умолчанию 2)
- `--base-port` или `-b`: базовый порт для серверов (по умолчанию 5000)
- `--proxy-port` или `-p`: порт для обратного прокси (по умолчанию 8000)
- `--algorithm` или `-a`: алгоритм балансировки (`round_robin`, `least_connections`, `ip_hash`)
- `--sticky-sessions` или `-s`: включить привязку сессий к серверам (по умолчанию выключено)

## Мониторинг кластера

### Проверка состояния серверов

Каждый сервер предоставляет эндпоинт `/health` для проверки состояния:

```bash
curl http://localhost:5000/health
```

Ответ:
```json
{
  "status": "healthy",
  "server_id": "server-1",
  "connections": 5,
  "threads": 8
}
```

### Статистика кластера

Обратный прокси предоставляет эндпоинт `/proxy/status` для просмотра статистики:

```bash
curl http://localhost:8000/proxy/status
```

Ответ:
```json
{
  "proxy_id": "abcd1234",
  "active_nodes": ["http://localhost:5000", "http://localhost:5001"],
  "node_stats": {
    "http://localhost:5000": {
      "connections": 3,
      "requests": 150,
      "errors": 0,
      "server_id": "server-1",
      "threads": 8
    },
    "http://localhost:5001": {
      "connections": 2,
      "requests": 120,
      "errors": 0,
      "server_id": "server-2",
      "threads": 8
    }
  },
  "algorithm": "round_robin",
  "sticky_sessions": false,
  "uptime": 3600
}
```

## Ручной запуск компонентов

Если вы хотите запустить компоненты кластера вручную:

### Запуск сервера

```bash
# Установка переменных окружения
export PORT=5000
export SERVER_ID="server-1"
export CLUSTER_MODE="true"
export CLUSTER_NODES='["http://localhost:5000", "http://localhost:5001"]'
export LOAD_BALANCING_ALGORITHM="round_robin"

# Запуск сервера
python run_server.py
```

### Запуск обратного прокси

```bash
python reverse_proxy.py --port 8000 --backends http://localhost:5000,http://localhost:5001 --algorithm round_robin
```

## Настройка для продакшн

### Настройка на нескольких физических серверах

Для настройки кластера на нескольких физических серверах:

1. Запустите сервер на каждой машине:

```bash
# На сервере 1 (IP: 192.168.1.10)
export PORT=5000
export SERVER_ID="server-1"
export CLUSTER_MODE="true"
export CLUSTER_NODES='["http://192.168.1.10:5000", "http://192.168.1.11:5000"]'
python run_server.py

# На сервере 2 (IP: 192.168.1.11)
export PORT=5000
export SERVER_ID="server-2"
export CLUSTER_MODE="true"
export CLUSTER_NODES='["http://192.168.1.10:5000", "http://192.168.1.11:5000"]'
python run_server.py
```

2. Запустите обратный прокси на отдельном сервере или на одном из серверов приложения:

```bash
python reverse_proxy.py --port 80 --backends http://192.168.1.10:5000,http://192.168.1.11:5000 --algorithm least_connections
```

### Интеграция с Nginx или HAProxy

Для более продвинутой настройки вы можете использовать Nginx или HAProxy вместо встроенного обратного прокси:

#### Пример конфигурации Nginx:

```nginx
upstream backend {
    # Round Robin (по умолчанию)
    server 192.168.1.10:5000;
    server 192.168.1.11:5000;
    
    # Для Least Connections
    # least_conn;
    
    # Для IP Hash
    # ip_hash;
    
    # Для sticky sessions
    # sticky cookie SERVERID;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Пример конфигурации HAProxy:

```
frontend http_front
    bind *:80
    default_backend http_back

backend http_back
    # Round Robin (по умолчанию)
    balance roundrobin
    
    # Для Least Connections
    # balance leastconn
    
    # Для sticky sessions
    # cookie SERVERID insert indirect nocache
    
    server server1 192.168.1.10:5000 check
    server server2 192.168.1.11:5000 check
```

## Устранение неполадок

### Проблема: Сервер не отвечает на запросы

1. Проверьте, что сервер запущен:
   ```bash
   curl http://localhost:5000/health
   ```

2. Проверьте логи сервера:
   ```bash
   cat server.log
   ```

### Проблема: Обратный прокси не распределяет запросы

1. Проверьте статус прокси:
   ```bash
   curl http://localhost:8000/proxy/status
   ```

2. Проверьте логи прокси:
   ```bash
   cat proxy.log
   ```

### Проблема: Кластер не запускается

1. Проверьте логи кластера:
   ```bash
   cat cluster.log
   ```

2. Убедитесь, что все порты свободны:
   ```bash
   netstat -tuln | grep 5000
   netstat -tuln | grep 8000
   ``` 