export default function Home() {
  return (
    <main className="min-h-screen bg-white px-6 py-20 text-black">
      <section className="mx-auto flex w-full max-w-4xl flex-col gap-8">
        <p className="text-xs font-semibold tracking-[0.2em] uppercase">
          CodexChat
        </p>
        <h1 className="max-w-2xl text-4xl font-semibold tracking-tight sm:text-6xl">
          Frontend bootstrap is live.
        </h1>
        <p className="max-w-2xl text-base text-zinc-700 sm:text-lg">
          This is the initial deployed shell for the CodexChat web app. Next
          updates will add login, chat, settings, and mobile-first app layout.
        </p>
      </section>
    </main>
  );
}
