#!/usr/bin/env python3
"""
Comprehensive test script for Knowledge Service (ChromaDB microservice)

This version matches the UPDATED API you now have:
- GET  /                     (root info)
- GET  /health
- GET  /stats/business
- GET  /stats/user
- POST /search               (supports user_id + brief_id)
- GET  /search/similar/{id}?which=business|user
- POST /add/business
- POST /add/business/bulk
- POST /add/user
- PUT  /update/{id}?which=business|user
- GET  /get/{id}?which=business|user
- GET  /list?which=business|user&brief_id=&category=&user_id=&limit=&offset=
- POST /test-embedding?text=...
- GET  /categories?which=business|user
- GET  /briefs?which=business|user
- POST /admin/seed?force=true|false
- POST /admin/reset?confirm=true
"""

import asyncio
import httpx
import json
import os
from typing import Dict, Any, List
from datetime import datetime

# Configuration
KNOWLEDGE_URL = os.getenv("KNOWLEDGE_URL", "http://localhost:8006")
TIMEOUT = httpx.Timeout(60.0, connect=10.0)

# Test data
TEST_BRIEF_ID = 999
TEST_USER_ID = "999999"

TEST_KNOWLEDGE_ITEMS = [
    {
        "text": "How to perform unit testing with pytest framework",
        "category": "faq",
        "title": "Unit Testing Guide",
        "metadata": {"difficulty": "beginner", "language": "python"},
    },
    {
        "text": "Integration testing ensures different modules work together correctly",
        "category": "general",
        "title": "Integration Testing",
        "metadata": {"type": "definition"},
    },
    {
        "text": "Our premium testing package costs $299/month and includes 24/7 support",
        "category": "price",
        "title": "Premium Package Pricing",
        "metadata": {"package": "premium"},
    },
]

TEST_USER_MEMORY_ITEMS = [
    {
        "user_id": TEST_USER_ID,
        "brief_id": TEST_BRIEF_ID,
        "category": "user_context",
        "title": "Lead profile",
        "text": "User prefers email communication. Budget under $500/month. Interested in automation.",
        "metadata": {"source": "test"},
    },
    {
        "user_id": TEST_USER_ID,
        "brief_id": TEST_BRIEF_ID,
        "category": "user_pref",
        "title": "Preferences",
        "text": "User dislikes long onboarding. Wants quick demo.",
        "metadata": {"source": "test"},
    },
]


class KnowledgeServiceTester:
    def __init__(self, base_url: str = KNOWLEDGE_URL):
        self.base_url = base_url.rstrip("/")
        self.client: httpx.AsyncClient | None = None

        # Track created docs to clean up
        self.created_business_ids: List[str] = []
        self.created_user_ids: List[str] = []

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup created documents
        await self.cleanup()
        if self.client:
            await self.client.aclose()

    async def cleanup(self):
        if not self.client:
            return

        total = len(self.created_business_ids) + len(self.created_user_ids)
        if total == 0:
            return

        print(f"\n🧹 Cleaning up {total} test documents...")

        # business
        for doc_id in self.created_business_ids:
            try:
                await self.client.delete(f"{self.base_url}/delete/{doc_id}", params={"which": "business"})
            except Exception:
                pass

        # user
        for doc_id in self.created_user_ids:
            try:
                await self.client.delete(f"{self.base_url}/delete/{doc_id}", params={"which": "user"})
            except Exception:
                pass

        self.created_business_ids.clear()
        self.created_user_ids.clear()

    # ---------------------------
    # Basic endpoints
    # ---------------------------
    async def test_root(self) -> Dict[str, Any]:
        print("\n🔍 Testing root endpoint...")
        try:
            r = await self.client.get(f"{self.base_url}/")
            r.raise_for_status()
            data = r.json()

            expected = ["message", "version", "ollama_host", "embedding_model", "business_collection", "user_collection"]
            ok = all(k in data for k in expected)
            if not ok:
                return {"status": "failed", "error": f"Missing fields. Got keys={list(data.keys())}"}

            print(f"✅ Root OK: {data.get('message')} v{data.get('version')}")
            return {"status": "passed", "response": data}
        except Exception as e:
            print(f"❌ Root failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_health(self) -> Dict[str, Any]:
        print("\n🔍 Testing health check...")
        try:
            r = await self.client.get(f"{self.base_url}/health")
            r.raise_for_status()
            data = r.json()

            expected = ["status", "chromadb", "ollama", "timestamp"]
            ok = all(k in data for k in expected)
            if not ok:
                return {"status": "failed", "error": f"Missing fields. Got keys={list(data.keys())}"}

            print(f"✅ Health OK: {data['status']} (chroma={data['chromadb']} ollama={data['ollama']})")
            return {"status": "passed", "response": data}
        except Exception as e:
            print(f"❌ Health failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ---------------------------
    # Add endpoints (business/user)
    # ---------------------------
    async def test_add_business(self) -> Dict[str, Any]:
        print("\n🔍 Testing add/business...")
        try:
            item = TEST_KNOWLEDGE_ITEMS[0].copy()
            item["brief_id"] = TEST_BRIEF_ID
            

            r = await self.client.post(f"{self.base_url}/add/business", json=item)
            r.raise_for_status()
            data = r.json()

            if data.get("status") != "success" or "document_id" not in data:
                return {"status": "failed", "error": f"Invalid response: {data}"}

            self.created_business_ids.append(data["document_id"])
            print(f"✅ add/business OK: {data['document_id']}")
            return {"status": "passed", "document_id": data["document_id"], "response": data}
        except Exception as e:
            print(f"❌ add/business failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_bulk_add_business(self) -> Dict[str, Any]:
        print("\n🔍 Testing add/business/bulk...")
        try:
            items = []
            for it in TEST_KNOWLEDGE_ITEMS:
                x = it.copy()
                x["brief_id"] = TEST_BRIEF_ID
                items.append(x)

            r = await self.client.post(f"{self.base_url}/add/business/bulk", json={"items": items})
            r.raise_for_status()
            data = r.json()

            if data.get("status") != "success" or data.get("added_count", 0) <= 0:
                return {"status": "failed", "error": f"Invalid response: {data}"}

            doc_ids = data.get("document_ids") or []
            self.created_business_ids.extend(doc_ids)

            print(f"✅ bulk add OK: added_count={data['added_count']}")
            return {"status": "passed", "added_count": data["added_count"], "response": data}
        except Exception as e:
            print(f"❌ bulk add failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_add_user(self) -> Dict[str, Any]:
        print("\n🔍 Testing add/user...")
        try:
            created = 0
            ids = []
            for item in TEST_USER_MEMORY_ITEMS:
                r = await self.client.post(f"{self.base_url}/add/user", json=item)
                r.raise_for_status()
                data = r.json()

                if data.get("status") != "success" or "document_id" not in data:
                    return {"status": "failed", "error": f"Invalid response: {data}"}

                self.created_user_ids.append(data["document_id"])
                ids.append(data["document_id"])
                created += 1

            print(f"✅ add/user OK: created={created}")
            return {"status": "passed", "created": created, "document_ids": ids}
        except Exception as e:
            print(f"❌ add/user failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ---------------------------
    # Search
    # ---------------------------
    async def test_search_business_only(self) -> Dict[str, Any]:
        print("\n🔍 Testing /search (business only)...")
        try:
            queries = [
                {"query": "pytest", "brief_id": TEST_BRIEF_ID, "top_k": 5},
                {"query": "premium package", "brief_id": TEST_BRIEF_ID, "category": "price", "top_k": 5},
            ]

            results = []
            for q in queries:
                r = await self.client.post(f"{self.base_url}/search", json=q)
                r.raise_for_status()
                data = r.json()

                expected = ["context", "sources", "total_found"]
                if not all(k in data for k in expected):
                    return {"status": "failed", "error": f"Missing fields for query={q}"}

                results.append(
                    {
                        "query": q["query"],
                        "total_found": data["total_found"],
                        "context_len": len(data["context"] or ""),
                    }
                )

            ok_count = sum(1 for x in results if x["total_found"] > 0)
            print(f"✅ search business OK: {ok_count}/{len(results)} queries returned >0")
            return {"status": "passed", "results": results}
        except Exception as e:
            print(f"❌ search business failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_search_with_user_memory(self) -> Dict[str, Any]:
        print("\n🔍 Testing /search (with user_id)...")
        try:
            q = {
                "query": "budget and demo",
                "brief_id": TEST_BRIEF_ID,
                "user_id": TEST_USER_ID,
                "top_k": 5,
            }
            r = await self.client.post(f"{self.base_url}/search", json=q)
            r.raise_for_status()
            data = r.json()

            # basic checks
            if "sources" not in data or "context" not in data:
                return {"status": "failed", "error": f"Invalid response keys={list(data.keys())}"}

            # count user/business sources
            srcs = data.get("sources") or []
            user_sources = [s for s in srcs if s.get("collection") == "user"]
            business_sources = [s for s in srcs if s.get("collection") == "business"]

            print(f"✅ search with user OK: user_sources={len(user_sources)} business_sources={len(business_sources)}")
            return {
                "status": "passed",
                "user_sources": len(user_sources),
                "business_sources": len(business_sources),
                "total_found": data.get("total_found", 0),
            }
        except Exception as e:
            print(f"❌ search with user failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ---------------------------
    # Stats, list, misc
    # ---------------------------
    async def test_stats(self) -> Dict[str, Any]:
        print("\n🔍 Testing /stats/business and /stats/user ...")
        try:
            rb = await self.client.get(f"{self.base_url}/stats/business")
            rb.raise_for_status()
            sb = rb.json()

            ru = await self.client.get(f"{self.base_url}/stats/user")
            ru.raise_for_status()
            su = ru.json()

            for data in (sb, su):
                expected = ["total_documents", "collection_name", "categories", "briefs"]
                if not all(k in data for k in expected):
                    return {"status": "failed", "error": f"Missing fields in stats: keys={list(data.keys())}"}

            print(f"✅ stats OK: business={sb['total_documents']} user={su['total_documents']}")
            return {"status": "passed", "business_total": sb["total_documents"], "user_total": su["total_documents"]}
        except Exception as e:
            print(f"❌ stats failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_list_and_get(self) -> Dict[str, Any]:
        print("\n🔍 Testing /list and /get ...")
        try:
            # list business for brief
            rb = await self.client.get(
                f"{self.base_url}/list",
                params={"which": "business", "brief_id": TEST_BRIEF_ID, "limit": 10},
            )
            rb.raise_for_status()
            lb = rb.json()
            if "items" not in lb:
                return {"status": "failed", "error": "List business missing 'items'"}

            # list user for user_id
            ru = await self.client.get(
                f"{self.base_url}/list",
                params={"which": "user", "brief_id": TEST_BRIEF_ID, "user_id": TEST_USER_ID, "limit": 10},
            )
            ru.raise_for_status()
            lu = ru.json()
            if "items" not in lu:
                return {"status": "failed", "error": "List user missing 'items'"}

            # get one business doc if available
            if lb["items"]:
                doc_id = lb["items"][0]["id"]
                rg = await self.client.get(f"{self.base_url}/get/{doc_id}", params={"which": "business"})
                rg.raise_for_status()
                gd = rg.json()
                if gd.get("id") != doc_id:
                    return {"status": "failed", "error": "Get business returned wrong id"}

            print(f"✅ list/get OK: business_list={len(lb['items'])} user_list={len(lu['items'])}")
            return {"status": "passed", "business_list": len(lb["items"]), "user_list": len(lu["items"])}
        except Exception as e:
            print(f"❌ list/get failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_update_delete(self) -> Dict[str, Any]:
        print("\n🔍 Testing update/delete (business)...")
        try:
            # create
            item = {
                "text": "Temporary document for update/delete testing",
                "brief_id": TEST_BRIEF_ID,
                "category": "test",
                "title": "Temporary Document",
                "metadata": {"test": True},
            }
            ra = await self.client.post(f"{self.base_url}/add/business", json=item)
            ra.raise_for_status()
            add_data = ra.json()
            doc_id = add_data["document_id"]
            self.created_business_ids.append(doc_id)

            # update
            upd = {
                "text": "Updated temporary document for testing",
                "category": "updated_test",
                "metadata": {"test": True, "updated": True},
                "title": "Temporary Document (Updated)",
            }
            ru = await self.client.put(f"{self.base_url}/update/{doc_id}", params={"which": "business"}, json=upd)
            ru.raise_for_status()

            # get and verify
            rg = await self.client.get(f"{self.base_url}/get/{doc_id}", params={"which": "business"})
            rg.raise_for_status()
            got = rg.json()
            meta = got.get("metadata") or {}
            if meta.get("updated") is not True or meta.get("category") != "updated_test":
                return {"status": "failed", "error": f"Update verification failed: metadata={meta}"}

            # delete
            rd = await self.client.delete(f"{self.base_url}/delete/{doc_id}", params={"which": "business"})
            rd.raise_for_status()

            # verify delete => 404
            rg2 = await self.client.get(f"{self.base_url}/get/{doc_id}", params={"which": "business"})
            if rg2.status_code != 404:
                return {"status": "failed", "error": f"Expected 404 after delete, got {rg2.status_code}"}

            # removed from cleanup list (already deleted)
            self.created_business_ids = [x for x in self.created_business_ids if x != doc_id]

            print("✅ update/delete OK")
            return {"status": "passed"}
        except Exception as e:
            print(f"❌ update/delete failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_test_embedding(self) -> Dict[str, Any]:
        print("\n🔍 Testing /test-embedding ...")
        try:
            text = "This is a test sentence for embedding generation"
            r = await self.client.post(f"{self.base_url}/test-embedding", params={"text": text})
            r.raise_for_status()
            data = r.json()

            expected = ["text", "embedding_size", "embedding_sample", "model"]
            if not all(k in data for k in expected):
                return {"status": "failed", "error": f"Missing fields: keys={list(data.keys())}"}

            print(f"✅ embedding OK: size={data['embedding_size']}")
            return {"status": "passed", "embedding_size": data["embedding_size"]}
        except Exception as e:
            print(f"❌ embedding failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_categories_briefs(self) -> Dict[str, Any]:
        print("\n🔍 Testing /categories and /briefs ...")
        try:
            rb = await self.client.get(f"{self.base_url}/categories", params={"which": "business"})
            rb.raise_for_status()
            cb = rb.json()

            ru = await self.client.get(f"{self.base_url}/categories", params={"which": "user"})
            ru.raise_for_status()
            cu = ru.json()

            bb = await self.client.get(f"{self.base_url}/briefs", params={"which": "business"})
            bb.raise_for_status()
            fb = bb.json()

            fu = await self.client.get(f"{self.base_url}/briefs", params={"which": "user"})
            fu.raise_for_status()
            fu_j = fu.json()

            print(f"✅ categories/briefs OK: business_cats={cb.get('total')} user_cats={cu.get('total')}")
            return {
                "status": "passed",
                "business_categories": cb.get("total", 0),
                "user_categories": cu.get("total", 0),
                "business_briefs": fb.get("total", 0),
                "user_briefs": fu_j.get("total", 0),
            }
        except Exception as e:
            print(f"❌ categories/briefs failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def test_error_handling(self) -> Dict[str, Any]:
        print("\n🔍 Testing error handling...")
        tests = [
            {
                "name": "Invalid search payload",
                "call": lambda: self.client.post(f"{self.base_url}/search", json={}),
                "expected": {400, 422},
            },
            {
                "name": "Non-existent get (business)",
                "call": lambda: self.client.get(f"{self.base_url}/get/non-existent-id", params={"which": "business"}),
                "expected": {404},
            },
            {
                "name": "Invalid add/business payload",
                "call": lambda: self.client.post(f"{self.base_url}/add/business", json={"text": ""}),
                "expected": {400, 422},
            },
            {
                "name": "Invalid which on list",
                "call": lambda: self.client.get(f"{self.base_url}/list", params={"which": "nope"}),
                "expected": {400},
            },
        ]

        results = []
        passed = 0
        for t in tests:
            try:
                r = await t["call"]()
                if r.status_code in t["expected"]:
                    print(f"✅ {t['name']}: {r.status_code}")
                    results.append({"test": t["name"], "status": "passed", "code": r.status_code})
                    passed += 1
                else:
                    print(f"❌ {t['name']}: unexpected {r.status_code}")
                    results.append({"test": t["name"], "status": "failed", "code": r.status_code, "body": r.text})
            except Exception as e:
                print(f"❌ {t['name']}: exception {e}")
                results.append({"test": t["name"], "status": "error", "error": str(e)})

        return {"status": "completed", "passed": passed, "total": len(tests), "results": results}

    # ---------------------------
    # Run suite
    # ---------------------------
    async def run_all_tests(self) -> Dict[str, Any]:
        print("🚀 Starting Knowledge Service Comprehensive Tests")
        print(f"📍 Testing URL: {self.base_url}")
        print("=" * 60)

        out: Dict[str, Any] = {}

        out["root"] = await self.test_root()
        out["health"] = await self.test_health()

        # Create test data
        out["add_business_single"] = await self.test_add_business()
        out["add_business_bulk"] = await self.test_bulk_add_business()
        out["add_user"] = await self.test_add_user()

        # Search tests
        out["search_business"] = await self.test_search_business_only()
        out["search_with_user"] = await self.test_search_with_user_memory()

        # Other endpoints
        out["stats"] = await self.test_stats()
        out["list_get"] = await self.test_list_and_get()
        out["update_delete"] = await self.test_update_delete()
        out["test_embedding"] = await self.test_test_embedding()
        out["categories_briefs"] = await self.test_categories_briefs()
        out["error_handling"] = await self.test_error_handling()

        # Summary
        core = [
            "root",
            "health",
            "add_business_single",
            "add_business_bulk",
            "add_user",
            "search_business",
            "search_with_user",
            "stats",
            "list_get",
            "update_delete",
            "test_embedding",
            "categories_briefs",
        ]

        passed_core = sum(1 for k in core if out.get(k, {}).get("status") == "passed")
        total_core = len(core)

        eh = out["error_handling"]
        passed_eh = eh.get("passed", 0)
        total_eh = eh.get("total", 0)

        overall_passed = passed_core + passed_eh
        overall_total = total_core + total_eh
        success_rate = round((overall_passed / overall_total) * 100, 2) if overall_total else 0.0

        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print(f"   Core: {passed_core}/{total_core}")
        print(f"   Error handling: {passed_eh}/{total_eh}")
        print(f"   Overall: {overall_passed}/{overall_total} ({success_rate}%)")
        print("=" * 60)

        out["summary"] = {
            "core_passed": passed_core,
            "core_total": total_core,
            "error_passed": passed_eh,
            "error_total": total_eh,
            "overall_passed": overall_passed,
            "overall_total": overall_total,
            "success_rate": success_rate,
        }

        return out


async def main():
    async with KnowledgeServiceTester() as tester:
        results = await tester.run_all_tests()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"knowledge_service_test_results_{ts}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Detailed results saved to {filename}")

        rate = results["summary"]["success_rate"]
        if rate >= 90:
            print("🎉 All tests passed successfully!")
            return 0
        if rate >= 75:
            print("⚠️  Most tests passed with some issues")
            return 1
        print("❌ Multiple test failures detected")
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
