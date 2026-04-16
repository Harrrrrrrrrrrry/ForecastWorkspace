export function ProjectNotes() {
  return (
    <div>
      <h2>Implementation Notes</h2>
      <ul className="list">
        <li>Backend forecasting logic stays in Python service modules.</li>
        <li>Frontend is responsible for input, charts, and result presentation.</li>
        <li>Reliability and warning signals are reserved in the response contract.</li>
        <li>AI explanations are strictly downstream of the quantitative model.</li>
      </ul>
    </div>
  );
}

