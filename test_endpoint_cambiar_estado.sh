#!/bin/bash

# Script para probar el endpoint de cambiar estado

echo "========================================="
echo "PROBANDO ENDPOINT CAMBIAR ESTADO"
echo "========================================="

# Primero obtener un token (ajusta según tu sistema de autenticación)
# TOKEN="tu_token_aqui"

# Probar cambiar estado
echo ""
echo "Probando POST /api/germinaciones/28601/cambiar-estado/"
echo "Body: {\"estado\": \"EN_PROCESO\"}"
echo ""

curl -X POST http://127.0.0.1:8000/api/germinaciones/28601/cambiar-estado/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"estado": "EN_PROCESO"}' \
  -v

echo ""
echo "========================================="
