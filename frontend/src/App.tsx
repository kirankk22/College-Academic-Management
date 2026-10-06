import { useEffect, useState } from "react";
import { getHealth } from "./services/api";

export default function App() {
  const [apiStatus, setApiStatus] = useState("Checking backend...");

  useEffect(() => {
    getHealth()
      .then((data) => setApiStatus(`${data.service}: ${data.status}`))
      .catch(() => setApiStatus("Backend unavailable"));
  }, []);

  return (
    <main style={{ fontFamily: "Arial, sans-serif", padding: 40 }}>
      <h1>College Academic Management</h1>
      <p>Phase 1 Foundation</p>
      <section
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 20,
          maxWidth: 600,
        }}
      >
        <h2>System Status</h2>
        <p>{apiStatus}</p>
      </section>
    </main>
  );
}
