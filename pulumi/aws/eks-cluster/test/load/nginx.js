import http from 'k6/http';
import { URL } from 'https://jslib.k6.io/url/1.0.0/index.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

export const options = {
  scenarios: {
    open_model: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 2,
      maxVUs: 10,
      startTime: '0s',
      stages: [
        { target: 10, duration: '5s' },
        { target: 50, duration: '120s' },
        { target: 10, duration: '5s' },
      ],
    },
  },
};

export default function () {

  const url = new URL('http://nginx.dev.lokalise.cloud');

  const res = http.get(url.toString());

  console.log('Response[' + res.status + ']: ' + res.timings.duration + 'ms');
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
  };
}
