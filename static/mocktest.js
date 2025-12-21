// small test runner - expects QUESTIONS global and TEST_ID injected
(function(){
  if(typeof QUESTIONS === 'undefined') return;
  const questions = QUESTIONS;
  const root = document.getElementById('test-root');

  let state = { current:0, answers: {} };

  function render(){
    const q = questions[state.current];
    root.innerHTML = `
      <div style="background:rgba(255,255,255,0.06); padding:18px; border-radius:10px;">
        <h4>Q${q.q_no}</h4>
        <p style="font-weight:600">${q.question}</p>
        <div id="opts"></div>
      </div>
      <div style="margin-top:12px;">
        <button id="prevBtn" class="hero-btn secondary">Prev</button>
        <button id="nextBtn" class="hero-btn primary">Next</button>
      </div>
    `;
    const opts = document.getElementById('opts');
    q.options.forEach((opt, idx)=>{
      const id = `opt_${q.id}_${idx}`;
      const checked = state.answers[q.id] === opt ? 'checked' : '';
      const item = document.createElement('div');
      item.innerHTML = `<label style="display:block; margin:8px 0;">
        <input type="radio" name="choice_${q.id}" value="${opt}" ${checked}> ${opt}
      </label>`;
      opts.appendChild(item);
    });

    document.getElementById('prevBtn').onclick = ()=> {
      if(state.current>0) { state.current--; render(); }
    };
    document.getElementById('nextBtn').onclick = ()=> {
      if(state.current < questions.length -1){
        state.current++; render();
      }
    };

    // attach change handler
    opts.querySelectorAll('input[type=radio]').forEach(r => {
      r.onchange = (e) => {
        state.answers[q.id] = e.target.value;
      };
    });
  }

  // submit
  document.getElementById('submit-btn').onclick = async function(){
    if(!confirm('Submit the test?')) return;
    // prepare answers map: question_id -> selected
    const answers = {};
    for(const q of questions){
      const sel = state.answers[q.id];
      answers[q.id] = sel || null;
    }
    const resp = await fetch(`/submit-test/${TEST_ID}`, {
      method:'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({answers})
    });
    const data = await resp.json();
    if(data && data.status === 'ok'){
      window.location.href = `/review/${data.attempt_id}`;
    } else {
      alert('Error submitting. Try again.');
    }
  };

  // initial render
  render();

})();
