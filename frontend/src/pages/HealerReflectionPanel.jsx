import React, { useEffect, useState, useRef, useCallback } from 'react';
import { HealerReflection } from '../components/healer/HealerReflection';
import { apiFetch } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

export function HealerReflectionPanel() {
  const [learnings, setLearnings] = useState([]);
  const [changes, setChanges] = useState([]);
  const [changesList, setChangesList] = useState([]);
  const processedRef = useRef(0);

  const { connected, messages } = useWebSocket();

  const load = useCallback(async () => {
    try {
      const r = await apiFetch('/api/v1/healer/bridge/reflection/latest');
      if (!r.ok) return;
      const d = await r.json();
      const reflection = d?.reflection || d;
      setLearnings(reflection?.learnings || []);
      setChanges(reflection?.changes || []);
    } catch (e) {
      // ignore
    }
  }, []);

  const loadChanges = useCallback(async () => {
    try {
      const r = await apiFetch('/api/v1/healer/bridge/changes?status=applied');
      if (!r.ok) return;
      const d = await r.json();
      if (d.changes) setChangesList(d.changes);
    } catch (e) {
      // ignore
    }
  }, []);

  // WS обработка
  useEffect(() => {
    if (messages.length > processedRef.current) {
      for (let i = processedRef.current; i < messages.length; i++) {
        const { type, data } = messages[i];
        if (type === 'healer_bridge_reflection') {
          setLearnings(data?.learnings || []);
          setChanges(data?.changes || []);
        }
        if (type === 'healer_bridge_cycle_complete') {
          loadChanges();
        }
      }
      processedRef.current = messages.length;
    }
  }, [messages, loadChanges]);

  // Polling каждые 30 сек
  useEffect(() => {
    load();
    loadChanges();
    const interval = setInterval(() => {
      load();
    }, 30000);
    return () => clearInterval(interval);
  }, [load, loadChanges]);

  const handleRollback = useCallback(async (change) => {
    if (!change?.patch_id) return;
    try {
      const r = await apiFetch(`/api/v1/healer/bridge/rollback/${change.patch_id}`, {
        method: 'POST',
      });
      if (r.ok) {
        load();
        loadChanges();
      }
    } catch (e) {
      // ignore
    }
  }, [load, loadChanges]);

  return <HealerReflection learnings={learnings} changes={changes} onRollback={handleRollback} />;
}

export default HealerReflectionPanel;

