const reservasCurso = Array.from(
  document.querySelectorAll("table tr")
)
  .slice(1)
  .map(tr => {
    const tds = tr.querySelectorAll("td");
    if (tds.length < 7) return null;

    const link = tds[0].querySelector("a");

    return {
      nome: tds[0].innerText.trim(),
      urlReserva: link?.href ?? null,
      departamento: tds[1].innerText.trim(),
      curso: tds[2].innerText.trim(),
      secao: tds[3].innerText.trim(),
      prazo: tds[4].innerText.trim(),
      instrutores: [
        ...new Set(
          tds[5].innerText
            .split(/[\n,]+/)
            .map(x => x.trim())
            .filter(Boolean)
        )
      ],
      notas: tds[6].innerText.trim()
    };
  })
  .filter(Boolean);

copy(JSON.stringify(reservasCurso, null, 2));

console.log(`Copiado ${reservasCurso.length} cursos para o clipboard.`);
