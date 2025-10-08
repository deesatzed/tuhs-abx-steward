#!/bin/bash
# Quick Local Testing Script for TUHS Antibiotic Steward

echo "========================================"
echo "TUHS Antibiotic Steward - Quick Tests"
echo "========================================"
echo ""

# Check if server is running
echo "1. Testing health endpoint..."
health=$(curl -s http://localhost:8080/health)
if echo "$health" | grep -q "healthy"; then
    echo "✅ Server is running"
else
    echo "❌ Server not responding. Start with: python fastapi_server.py"
    exit 1
fi
echo ""

# Test 1: Simple Pyelonephritis
echo "2. Testing simple pyelonephritis case..."
result=$(curl -s -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"age":"45","gender":"female","location":"Ward","infection_type":"pyelonephritis","gfr":"85","allergies":"None"}')

if echo "$result" | grep -qi "ceftriaxone"; then
    echo "✅ PASS: Ceftriaxone recommended for pyelonephritis"
else
    echo "❌ FAIL: Ceftriaxone NOT found in recommendation"
    echo "$result" | python -m json.tool | grep tuhs_recommendation
fi

if echo "$result" | grep -qi "ciprofloxacin"; then
    echo "⚠️  WARNING: Ciprofloxacin mentioned (should be Ceftriaxone first-line)"
fi
echo ""

# Test 2: Critical - Anaphylaxis Safety
echo "3. Testing CRITICAL safety: Anaphylaxis + Bacteremia..."
result=$(curl -s -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"age":"88","gender":"male","location":"Ward","infection_type":"bacteremia","gfr":"44","allergies":"Penicillin (anaphylaxis)","inf_risks":"MRSA colonization"}')

has_aztreonam=$(echo "$result" | grep -qi "aztreonam" && echo "yes" || echo "no")
has_vancomycin=$(echo "$result" | grep -qi "vancomycin" && echo "yes" || echo "no")
has_cefepime=$(echo "$result" | grep -qi "cefepime" && echo "yes" || echo "no")
has_ceftriaxone=$(echo "$result" | grep -qi "ceftriaxone" && echo "yes" || echo "no")

if [ "$has_aztreonam" = "yes" ] && [ "$has_vancomycin" = "yes" ]; then
    echo "✅ PASS: Aztreonam + Vancomycin recommended"
else
    echo "❌ FAIL: Expected Aztreonam + Vancomycin"
fi

if [ "$has_cefepime" = "yes" ] || [ "$has_ceftriaxone" = "yes" ]; then
    echo "❌ CRITICAL SAFETY VIOLATION: Cephalosporin recommended for anaphylaxis!"
    echo "$result" | python -m json.tool | grep tuhs_recommendation
    exit 1
else
    echo "✅ PASS: No cephalosporins for anaphylaxis (correct)"
fi
echo ""

# Test 3: Pregnancy Safety
echo "4. Testing CRITICAL safety: Pregnancy..."
result=$(curl -s -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"age":"28","gender":"female","location":"Ward","infection_type":"pyelonephritis","gfr":"95","allergies":"None","inf_risks":"Pregnancy - 26 weeks gestation"}')

has_ceftriaxone=$(echo "$result" | grep -qi "ceftriaxone" && echo "yes" || echo "no")
rec=$(echo "$result" | python -m json.tool | grep '"tuhs_recommendation"' | head -1)

# Check if fluoroquinolones are in the PRIMARY recommendation
if echo "$rec" | grep -Eqi "ciprofloxacin|levofloxacin|moxifloxacin"; then
    echo "❌ CRITICAL SAFETY VIOLATION: Fluoroquinolone in primary recommendation for pregnancy!"
    echo "$rec"
    exit 1
else
    echo "✅ PASS: No fluoroquinolones in primary recommendation"
fi

if [ "$has_ceftriaxone" = "yes" ]; then
    echo "✅ PASS: Ceftriaxone recommended (safe in pregnancy)"
else
    echo "⚠️  WARNING: Ceftriaxone not found"
fi
echo ""

# Summary
echo "========================================"
echo "Quick Test Summary"
echo "========================================"
echo "✅ All critical safety tests passed!"
echo ""
echo "To run full test suite:"
echo "  pytest tests/ -v"
echo ""
echo "To run only critical tests:"
echo "  pytest tests/ -v -m critical"
echo ""
echo "Server is running at: http://localhost:8080"
echo "API docs at: http://localhost:8080/docs"
