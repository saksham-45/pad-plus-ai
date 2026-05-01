import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion } from 'framer-motion';

const pipelineSteps = [
  { id: 'input', label: 'Input', color: 'bg-gray-600' },
  { id: 'safety', label: 'Safety', color: 'bg-blue-600' },
  { id: 'intent', label: 'Intent', color: 'bg-cyan-600' },
  { id: 'retrieve', label: 'Retrieve', color: 'bg-green-600' },
  { id: 'persona', label: 'Persona', color: 'bg-yellow-600' },
  { id: 'generate', label: 'Generate', color: 'bg-orange-600' },
  { id: 'truth', label: 'Truth', color: 'bg-red-600' },
  { id: 'remember', label: 'Remember', color: 'bg-purple-600' },
  { id: 'output', label: 'Output', color: 'bg-pink-600' },
];

export function FlowWidget({ activeStep, status = 'idle' }) {
  return (
    <Card hover className="h-full">
      <CardHeader>
        <CardTitle>AI Pipeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between gap-1 overflow-x-auto pb-2">
          {pipelineSteps.map((step, index) => (
            <div key={step.id} className="flex items-center flex-1 min-w-0">
              <motion.div
                className={`flex items-center justify-center w-10 h-10 rounded-lg text-xs font-medium transition-all ${
                  activeStep === step.id
                    ? `${step.color} ring-2 ring-primary ring-offset-2 ring-offset-background`
                    : 'bg-gray-800 text-text-muted'
                }`}
                animate={{
                  scale: activeStep === step.id ? 1.1 : 1,
                  opacity: activeStep === step.id ? 1 : 0.6,
                }}
              >
                {step.label}
              </motion.div>
              {index < pipelineSteps.length - 1 && (
                <motion.div
                  className={`flex-1 h-0.5 mx-1 ${
                    pipelineSteps.findIndex(s => s.id === activeStep) > index
                      ? 'bg-primary'
                      : 'bg-gray-700'
                  }`}
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: index * 0.05 }}
                />
              )}
            </div>
          ))}
        </div>
        
        {status !== 'idle' && (
          <div className="mt-4 text-center">
            <span className={`text-xs px-2 py-1 rounded ${
              status === 'processing'
                ? 'bg-primary/20 text-primary'
                : status === 'success'
                ? 'bg-green-600/20 text-green-500'
                : 'bg-red-600/20 text-red-500'
            }`}>
              {status === 'processing' && 'Processing...'}
              {status === 'success' && 'Complete'}
              {status === 'error' && 'Error'}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default FlowWidget;