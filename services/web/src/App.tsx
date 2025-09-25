import { useState } from "react";
import { Header } from "./components/Header";
import { HoldersList } from "./components/HoldersList";

function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="min-h-dvh bg-gray-50 text-gray-900">
      <Header />
      <main className="mx-auto max-w-6xl p-4">
        <HoldersList />
      </main>
    </div>
  );
}

export default App;
