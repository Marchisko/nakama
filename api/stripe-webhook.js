import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export const config = { api: { bodyParser: false } };

async function buffer(readable) {
  const chunks = [];
  for await (const chunk of readable) chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : chunk);
  return Buffer.concat(chunks);
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();

  const sig = req.headers['stripe-signature'];
  const buf = await buffer(req);

  let event;
  try {
    event = stripe.webhooks.constructEvent(buf, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  if (event.type === 'customer.subscription.created' || event.type === 'customer.subscription.updated') {
    const subscription = event.data.object;
    const customerId = subscription.customer;
    const isActive = subscription.status === 'active' || subscription.status === 'trialing';

    // Get customer email from Stripe
    const customer = await stripe.customers.retrieve(customerId);
    const email = customer.email;
    if (!email) return res.json({ received: true });

    // Find user in Supabase by email
    const { data: { users } } = await supabase.auth.admin.listUsers();
    const user = users.find(u => u.email === email);
    if (!user) return res.json({ received: true });

    // Update is_premium in profiles
    await supabase.from('profiles').update({ is_premium: isActive }).eq('id', user.id);
  }

  if (event.type === 'customer.subscription.deleted') {
    const subscription = event.data.object;
    const customer = await stripe.customers.retrieve(subscription.customer);
    const email = customer.email;
    if (!email) return res.json({ received: true });

    const { data: { users } } = await supabase.auth.admin.listUsers();
    const user = users.find(u => u.email === email);
    if (user) await supabase.from('profiles').update({ is_premium: false }).eq('id', user.id);
  }

  res.json({ received: true });
}
