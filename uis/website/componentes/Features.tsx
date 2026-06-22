export type FeatureItem = {
  title: string;
  description: string;
};

type FeaturesProps = {
  headingId: string;
  title: string;
  description: string;
  items: FeatureItem[];
  backgroundClassName?: string;
  borderedCards?: boolean;
};

type FeatureCardProps = FeatureItem & {
  bordered?: boolean;
};

function FeatureCard({ title, description, bordered = false }: FeatureCardProps) {
  return (
    <article
      className={[
        "rounded-xl p-6",
        bordered ? "border border-gray-200 transition hover:shadow-md" : "",
      ].join(" ")}
    >
      <h3 className="mb-2 text-xl font-semibold text-gray-900">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </article>
  );
}

export function Features({
  headingId,
  title,
  description,
  items,
  backgroundClassName = "bg-white",
  borderedCards = false,
}: FeaturesProps) {
  return (
    <section aria-labelledby={headingId} className={`${backgroundClassName} px-6 py-20`}>
      <div className="mx-auto max-w-6xl text-center">
        <h2 id={headingId} className="mb-4 text-3xl font-bold text-gray-900">
          {title}
        </h2>
        <p className="mx-auto mb-12 max-w-2xl text-gray-600">{description}</p>

        <div className="grid gap-8 text-left md:grid-cols-3">
          {items.map((item) => (
            <FeatureCard
              key={item.title}
              title={item.title}
              description={item.description}
              bordered={borderedCards}
            />
          ))}
        </div>
      </div>
    </section>
  );
}