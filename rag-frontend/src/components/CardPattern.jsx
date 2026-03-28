import React from 'react';
import '../cardPattern.css';

export default function CardPattern() {
  return (
    <div className="pattern-container" aria-hidden="true">
      <div className="pattern-stars" />
      <div className="pattern-stars2" />
      <div className="pattern-stars3" />
    </div>
  );
}
