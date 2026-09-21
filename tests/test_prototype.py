import os
import tempfile
import unittest
from pathlib import Path

tmp = tempfile.TemporaryDirectory()
os.environ["APP_DB_PATH"] = str(Path(tmp.name) / "test.db")

from app import database as db
from app import domain, service

class PrototypeTest(unittest.TestCase):
    def setUp(self):
        db.init_db()
        db.reset_db()

    def test_status_is_grounded_and_owned(self):
        item = service.create("cliente-ana", "Canal Vértice", "Onde está o pedido VERT-1001?")
        self.assertEqual(item["route"], "CHATBOT")
        self.assertIn("Em transporte", item["messages"][-1]["text"])
        blocked = service.create("cliente-bruno", "WhatsApp", "Onde está o pedido VERT-1001?")
        self.assertEqual(blocked["status"], "waiting_human")
        self.assertNotIn("Em transporte", blocked["messages"][-1]["text"])

    def test_order_code_continues_status_conversation(self):
        item = service.create("cliente-ana", "Canal Vértice", "Quero saber onde está meu pedido")
        followed = service.client_message("cliente-ana", item["id"], "VERT-1001")
        self.assertEqual(followed["route"], "CHATBOT")
        self.assertIn("Em transporte", followed["messages"][-1]["text"])

    def test_fraud_is_p0_and_specialized(self):
        item = service.create("cliente-ana", "WhatsApp", "Tem uma cobrança que não reconheço")
        self.assertEqual((item["priority"], item["team"], item["route"]), ("P0", "Financeiro", "HUMANO_ESPECIALIZADO"))

    def test_general_question_is_refused(self):
        item = service.create("cliente-ana", "Canal Vértice", "Qual é a capital da França?")
        self.assertEqual(item["route"], "FORA_DE_ESCOPO")
        self.assertIn("somente", item["messages"][-1]["text"])

    def test_team_access_is_enforced(self):
        finance = next(x for x in db.conversations() if x["team"] == "Financeiro")
        with self.assertRaises(PermissionError):
            service.get_for_actor("posvenda-01", finance["id"])
        self.assertEqual(service.get_for_actor("financeiro-01", finance["id"])["id"], finance["id"])

    def test_human_reply_uses_same_history(self):
        item = service.create("cliente-carla", "E-mail", "Quero trocar o tamanho")
        replied = service.operator_message("posvenda-01", item["id"], "Olá, vou continuar sua solicitação.")
        self.assertEqual(replied["messages"][-1]["author_type"], "agent")
        self.assertEqual(service.get_for_customer("cliente-carla", item["id"])["messages"][-1]["text"], "Olá, vou continuar sua solicitação.")

    def test_bot_stays_silent_after_handoff(self):
        item = service.create("cliente-ana", "WhatsApp", "Tem uma cobrança que não reconheço")
        count = len(item["messages"])
        followed = service.client_message("cliente-ana", item["id"], "Posso mandar uma foto?")
        self.assertEqual(len(followed["messages"]), count + 1)
        self.assertEqual(followed["messages"][-1]["author_type"], "customer")
        self.assertEqual(followed["status"], "waiting_human")

if __name__ == "__main__":
    unittest.main()
